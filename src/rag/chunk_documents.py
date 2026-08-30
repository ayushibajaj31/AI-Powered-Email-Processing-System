"""Split knowledge-base documents into metadata-rich, retrieval-ready chunks.

This step only creates chunks; it does not create embeddings or perform search.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path


DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100


def project_root():
    return Path(__file__).resolve().parents[2]


def load_metadata(knowledge_base):
    return json.loads((knowledge_base / "metadata.json").read_text(encoding="utf-8"))


def split_long_segment(segment, chunk_size):
    """Use word boundaries only when one sentence is longer than a whole chunk."""
    words = segment.split()
    pieces, current = [], []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > chunk_size:
            pieces.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        pieces.append(" ".join(current))
    return pieces


def trailing_context(text, overlap):
    """Keep whole trailing sentences where practical, avoiding mid-sentence cuts."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    selected = []
    for sentence in reversed(sentences):
        candidate = " ".join([sentence] + selected)
        if selected and len(candidate) > overlap:
            break
        selected.insert(0, sentence)
    return " ".join(selected)


def split_text(text, chunk_size=DEFAULT_CHUNK_SIZE, chunk_overlap=DEFAULT_CHUNK_OVERLAP):
    """Make coherent sentence-based chunks with optional context overlap."""
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and chunk_overlap must be smaller than chunk_size.")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]
    segments = []
    for paragraph in paragraphs:
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            if sentence:
                segments.extend(split_long_segment(sentence, chunk_size) if len(sentence) > chunk_size else [sentence])

    chunks, current = [], ""
    for segment in segments:
        candidate = f"{current} {segment}".strip()
        if current and len(candidate) > chunk_size:
            chunks.append(current)
            context = trailing_context(current, chunk_overlap)
            current = f"{context} {segment}".strip()
            # A long word-based segment may not leave room for overlap.
            if len(current) > chunk_size:
                current = segment
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def create_chunks(knowledge_base, chunk_size, chunk_overlap):
    chunks = []
    for entry in load_metadata(knowledge_base):
        document_path = knowledge_base / entry["file_name"]
        text = document_path.read_text(encoding="utf-8").strip()
        for index, chunk_text in enumerate(split_text(text, chunk_size, chunk_overlap)):
            chunks.append({
                "chunk_id": f"{entry['document_id']}_CHUNK_{index + 1:03d}",
                "text": chunk_text,
                "metadata": {
                    "chunk_id": f"{entry['document_id']}_CHUNK_{index + 1:03d}",
                    "document_id": entry["document_id"],
                    "source_file": Path(entry["file_name"]).name,
                    "category": entry["category"],
                    "topic": entry["topic"],
                    "source": entry["source"],
                    "version": entry["version"],
                    "chunk_index": index,
                },
            })
    return chunks


def print_statistics(chunks, source_document_count):
    lengths = [len(chunk["text"]) for chunk in chunks]
    counts = Counter(chunk["metadata"]["category"] for chunk in chunks)
    print(f"Source documents: {source_document_count}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Minimum chunk length: {min(lengths)}")
    print(f"Maximum chunk length: {max(lengths)}")
    print(f"Average chunk length: {sum(lengths) / len(lengths):.2f}")
    print(f"Average chunks per document: {len(chunks) / source_document_count:.2f}")
    print("Chunks per category:")
    for category, count in sorted(counts.items()):
        print(f"  {category}: {count}")
    print("Example chunks:")
    for chunk in chunks[:5]:
        metadata = chunk["metadata"]
        print(f"  {chunk['chunk_id']} | {metadata['category']} | {metadata['topic']}")
        print(f"  {chunk['text']}")


def main():
    parser = argparse.ArgumentParser(description="Chunk knowledge-base documents without creating embeddings.")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    args = parser.parse_args()

    knowledge_base = project_root() / "data" / "knowledge_base"
    chunks_directory = project_root() / "data" / "chunks"
    metadata = load_metadata(knowledge_base)
    chunks = create_chunks(knowledge_base, args.chunk_size, args.chunk_overlap)
    chunks_directory.mkdir(parents=True, exist_ok=True)
    (chunks_directory / "knowledge_chunks.json").write_text(json.dumps(chunks, indent=2) + "\n", encoding="utf-8")
    print_statistics(chunks, len(metadata))
    print(f"Saved chunks to: {chunks_directory / 'knowledge_chunks.json'}")


if __name__ == "__main__":
    main()

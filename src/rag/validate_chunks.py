"""Validate chunk content, metadata, and source-document coverage."""

import json
from collections import Counter
from pathlib import Path


REQUIRED_METADATA = {"chunk_id", "document_id", "source_file", "category", "topic", "source", "version", "chunk_index"}
IMPORTANT_TERMS = ["return", "refund", "exchange", "cancellation", "shipping", "warranty", "days", "business days"]


def project_root():
    return Path(__file__).resolve().parents[2]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_chunks(chunks, source_metadata):
    ids = [chunk.get("chunk_id", "") for chunk in chunks]
    texts = [chunk.get("text", "").strip() for chunk in chunks]
    duplicate_texts = [text for text, count in Counter(texts).items() if text and count > 1]
    metadata_errors, index_errors = [], []
    produced_document_ids = set()
    indices_by_document = {}
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        missing = REQUIRED_METADATA - set(metadata)
        if missing or any(str(metadata.get(field, "")).strip() == "" for field in REQUIRED_METADATA):
            metadata_errors.append(chunk.get("chunk_id", "unknown"))
            continue
        produced_document_ids.add(metadata["document_id"])
        indices_by_document.setdefault(metadata["document_id"], []).append(metadata["chunk_index"])
        if metadata["chunk_id"] != chunk.get("chunk_id"):
            metadata_errors.append(chunk.get("chunk_id", "unknown"))
    for document_id, indices in indices_by_document.items():
        if sorted(indices) != list(range(len(indices))):
            index_errors.append(document_id)
    source_document_ids = {entry["document_id"] for entry in source_metadata}
    all_text = " ".join(texts).casefold()
    missing_terms = [term for term in IMPORTANT_TERMS if term not in all_text]
    return {
        "total_chunks": len(chunks),
        "empty_chunks": sum(not text for text in texts),
        "duplicate_chunk_ids": len(ids) - len(set(ids)),
        "duplicate_chunk_texts": len(duplicate_texts),
        "metadata_errors": metadata_errors,
        "documents_without_chunks": sorted(source_document_ids - produced_document_ids),
        "invalid_chunk_indices": index_errors,
        "missing_important_terms": missing_terms,
    }


def write_report(path, results):
    lines = ["CHUNK VALIDATION REPORT", "=" * 60]
    for key, value in results.items():
        lines.append(f"{key.replace('_', ' ').title()}: {value if value else 'None'}")
    passed = all(not value for key, value in results.items() if key != "total_chunks")
    lines.extend(["", "Final status: PASSED" if passed else "Final status: FAILED — review findings above."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    root = project_root()
    chunks_directory = root / "data" / "chunks"
    chunks_path = chunks_directory / "knowledge_chunks.json"
    if not chunks_path.exists():
        raise FileNotFoundError("Chunks not found. Run src/rag/chunk_documents.py first.")
    chunks = load_json(chunks_path)
    source_metadata = load_json(root / "data" / "knowledge_base" / "metadata.json")
    results = validate_chunks(chunks, source_metadata)
    write_report(chunks_directory / "chunk_report.txt", results)
    passed = all(not value for key, value in results.items() if key != "total_chunks")
    print(f"Chunks validated: {results['total_chunks']}")
    print(f"Validation status: {'PASSED' if passed else 'FAILED'}")
    print(f"Report: {chunks_directory / 'chunk_report.txt'}")


if __name__ == "__main__":
    main()

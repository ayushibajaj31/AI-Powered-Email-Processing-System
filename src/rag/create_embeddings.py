"""Generate local sentence-transformer embeddings for knowledge-base chunks.

This script stores vectors only. It does not create a vector database or search.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 32


def project_root():
    return Path(__file__).resolve().parents[2]


def load_chunks(path):
    chunks = json.loads(path.read_text(encoding="utf-8"))
    if not chunks or any(not chunk.get("text", "").strip() for chunk in chunks):
        raise ValueError("knowledge_chunks.json must contain non-empty chunk text.")
    return chunks


def create_embeddings(texts, batch_size):
    """Load the local model and batch-encode normalized sentence embeddings."""
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(
        texts, batch_size=batch_size, show_progress_bar=True,
        normalize_embeddings=True, convert_to_numpy=True,
    )
    return embeddings.astype(np.float32)


def save_embedded_chunks(path, chunks):
    records = []
    for index, chunk in enumerate(chunks):
        records.append({
            "chunk_id": chunk["chunk_id"], "text": chunk["text"],
            "metadata": chunk["metadata"], "embedding_index": index,
        })
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Create all-MiniLM-L6-v2 chunk embeddings locally.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    if args.batch_size <= 0:
        raise ValueError("batch-size must be positive.")

    root = project_root()
    chunks = load_chunks(root / "data" / "chunks" / "knowledge_chunks.json")
    embeddings = create_embeddings([chunk["text"] for chunk in chunks], args.batch_size)
    if embeddings.ndim != 2 or len(embeddings) != len(chunks):
        raise RuntimeError("Embedding output does not match the number of chunks.")

    output = root / "data" / "embeddings"
    output.mkdir(parents=True, exist_ok=True)
    np.save(output / "embeddings.npy", embeddings)
    save_embedded_chunks(output / "embedded_chunks.json", chunks)
    print(f"Embedding model: {MODEL_NAME}")
    print(f"Number of chunks: {len(chunks)}")
    print(f"Number of embeddings: {len(embeddings)}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Data type: {embeddings.dtype}")
    print(f"Saved vectors to: {output / 'embeddings.npy'}")
    print(f"Saved references to: {output / 'embedded_chunks.json'}")


if __name__ == "__main__":
    main()

"""Build a local FAISS index from normalized knowledge-base embeddings."""

import json
from pathlib import Path

import faiss
import numpy as np


def project_root():
    return Path(__file__).resolve().parents[2]


def main():
    root = project_root()
    embeddings_directory = root / "data" / "embeddings"
    vectors = np.load(embeddings_directory / "embeddings.npy").astype(np.float32)
    chunks = json.loads((embeddings_directory / "embedded_chunks.json").read_text(encoding="utf-8"))
    if vectors.ndim != 2 or len(vectors) != len(chunks):
        raise ValueError("Embedding vectors and embedded chunk records must have matching two-dimensional data.")
    if not np.isfinite(vectors).all():
        raise ValueError("Embeddings contain NaN or infinite values.")

    # Step 8 normalized the vectors, so inner product equals cosine similarity.
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    mapping = {}
    for position, record in enumerate(chunks):
        metadata = record.get("metadata", {})
        mapping[str(position)] = {
            "chunk_id": record["chunk_id"], "text": record["text"],
            "metadata": {
                "document_id": metadata["document_id"], "category": metadata["category"],
                "topic": metadata["topic"], "source_file": metadata["source_file"],
                "source": metadata["source"], "version": metadata["version"],
            },
        }
    output = root / "data" / "vector_store"
    output.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(output / "faiss.index"))
    (output / "chunk_metadata.json").write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    print(f"Vectors indexed: {index.ntotal}")
    print(f"Embedding dimension: {index.d}")
    print("Index type: IndexFlatIP (cosine similarity for normalized vectors)")
    print(f"Saved index: {output / 'faiss.index'}")
    print(f"Saved metadata: {output / 'chunk_metadata.json'}")


if __name__ == "__main__":
    main()

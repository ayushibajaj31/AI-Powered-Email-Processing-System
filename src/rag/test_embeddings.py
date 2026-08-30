"""Run a direct cosine-similarity sanity check without a vector database."""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
QUERIES = [
    "Where is my order?", "Can I exchange my shoes for another size?",
    "How long does a refund take?", "Can I cancel my order?",
    "What payment methods do you accept?",
]


def project_root():
    return Path(__file__).resolve().parents[2]


def main():
    root = project_root()
    output = root / "data" / "embeddings"
    vectors = np.load(output / "embeddings.npy")
    chunks = json.loads((output / "embedded_chunks.json").read_text(encoding="utf-8"))
    if len(vectors) != len(chunks):
        raise ValueError("Embedding count does not match embedded chunk count.")
    model = SentenceTransformer(MODEL_NAME)
    queries = model.encode(QUERIES, normalize_embeddings=True, convert_to_numpy=True)
    # Vectors and queries are normalized, so dot product equals cosine similarity.
    scores = queries @ vectors.T
    for query, row in zip(QUERIES, scores):
        print(f"\nQuery: {query}")
        for index in np.argsort(row)[-3:][::-1]:
            record = chunks[int(index)]
            metadata = record["metadata"]
            preview = record["text"].replace("\n", " ")[:180]
            print(f"  {record['chunk_id']} | {metadata['category']} / {metadata['topic']} | similarity: {row[index]:.4f}")
            print(f"  {preview}")


if __name__ == "__main__":
    main()

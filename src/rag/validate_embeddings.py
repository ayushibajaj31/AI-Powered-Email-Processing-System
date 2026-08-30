"""Validate saved knowledge-base embeddings and their chunk references."""

import json
from pathlib import Path

import numpy as np


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
REQUIRED_METADATA = {"document_id", "category", "topic", "source_file", "source", "version"}


def project_root():
    return Path(__file__).resolve().parents[2]


def main():
    output = project_root() / "data" / "embeddings"
    vectors_path, chunks_path = output / "embeddings.npy", output / "embedded_chunks.json"
    if not vectors_path.exists() or not chunks_path.exists():
        raise FileNotFoundError("Embedding files not found. Run src/rag/create_embeddings.py first.")
    vectors = np.load(vectors_path)
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    indices = [record.get("embedding_index") for record in chunks]
    invalid_metadata = [record.get("chunk_id", "unknown") for record in chunks if not REQUIRED_METADATA.issubset(record.get("metadata", {}))]
    invalid_indices = [index for index in indices if not isinstance(index, int) or index < 0 or index >= len(vectors)]
    norms = np.linalg.norm(vectors, axis=1) if vectors.ndim == 2 else np.array([])
    invalid_embeddings = int((~np.isfinite(vectors)).any(axis=1).sum()) if vectors.ndim == 2 else len(vectors)
    report = {
        "embedding_model": MODEL_NAME, "number_of_chunks": len(chunks), "number_of_embeddings": len(vectors),
        "embedding_dimension": int(vectors.shape[1]) if vectors.ndim == 2 else 0, "data_type": str(vectors.dtype),
        "invalid_embeddings": invalid_embeddings, "missing_chunk_metadata": len(invalid_metadata),
        "invalid_embedding_indices": len(invalid_indices), "minimum_vector_norm": float(norms.min()) if len(norms) else 0.0,
        "maximum_vector_norm": float(norms.max()) if len(norms) else 0.0,
        "average_vector_norm": float(norms.mean()) if len(norms) else 0.0,
    }
    valid = (len(chunks) == len(vectors) and vectors.ndim == 2 and invalid_embeddings == 0
             and not invalid_metadata and not invalid_indices and sorted(indices) == list(range(len(vectors))))
    lines = ["EMBEDDING VALIDATION REPORT", "=" * 60]
    lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in report.items())
    lines.extend(["", "Final status: PASSED" if valid else "Final status: FAILED — review findings above."])
    (output / "embedding_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Embeddings validated: {len(vectors)}")
    print(f"Embedding dimension: {report['embedding_dimension']}")
    print(f"Validation status: {'PASSED' if valid else 'FAILED'}")
    print(f"Report: {output / 'embedding_report.txt'}")


if __name__ == "__main__":
    main()

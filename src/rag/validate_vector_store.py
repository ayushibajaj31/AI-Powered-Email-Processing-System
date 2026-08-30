"""Validate a local FAISS index and its metadata position mapping."""

import json
from pathlib import Path

import faiss
import numpy as np


def project_root():
    return Path(__file__).resolve().parents[2]


def main():
    root = project_root()
    store, embeddings = root / "data" / "vector_store", root / "data" / "embeddings"
    index_path, metadata_path = store / "faiss.index", store / "chunk_metadata.json"
    if not index_path.exists() or not metadata_path.exists():
        raise FileNotFoundError("Vector-store files are missing. Run src/rag/build_vector_store.py first.")
    index = faiss.read_index(str(index_path))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    vectors = np.load(embeddings / "embeddings.npy")
    required = {"chunk_id", "text", "metadata"}
    required_metadata = {"document_id", "category", "topic", "source_file", "source", "version"}
    missing_records = [position for position in range(index.ntotal) if str(position) not in metadata]
    invalid_metadata = [key for key, record in metadata.items() if not required.issubset(record) or not required_metadata.issubset(record.get("metadata", {}))]
    chunk_ids = [record.get("chunk_id") for record in metadata.values()]
    report = {
        "faiss_index_exists": index_path.exists(), "metadata_file_exists": metadata_path.exists(),
        "faiss_vector_count": index.ntotal, "metadata_count": len(metadata), "embedding_dimension": int(vectors.shape[1]),
        "faiss_dimension": index.d, "missing_metadata_positions": missing_records,
        "duplicate_chunk_ids": len(chunk_ids) - len(set(chunk_ids)), "invalid_or_missing_metadata": invalid_metadata,
    }
    passed = (index.ntotal == len(metadata) == len(vectors) and index.d == vectors.shape[1]
              and not missing_records and not invalid_metadata and report["duplicate_chunk_ids"] == 0)
    lines = ["VECTOR STORE VALIDATION REPORT", "=" * 60]
    lines.extend(f"{key.replace('_', ' ').title()}: {value if value else 'None'}" for key, value in report.items())
    lines.extend(["", "Final status: PASSED" if passed else "Final status: FAILED — review findings above."])
    (store / "vector_store_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"FAISS vectors: {index.ntotal}")
    print(f"Validation status: {'PASSED' if passed else 'FAILED'}")
    print(f"Report: {store / 'vector_store_report.txt'}")


if __name__ == "__main__":
    main()

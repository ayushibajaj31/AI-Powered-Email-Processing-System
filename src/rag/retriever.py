"""Reusable FAISS semantic retriever for the local knowledge base."""

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class VectorRetriever:
    def __init__(self, top_k=5, score_threshold=None):
        self.top_k = top_k
        self.score_threshold = score_threshold
        root = Path(__file__).resolve().parents[2]
        store = root / "data" / "vector_store"
        self.index = faiss.read_index(str(store / "faiss.index"))
        self.metadata = json.loads((store / "chunk_metadata.json").read_text(encoding="utf-8"))
        self.model = SentenceTransformer(MODEL_NAME)

    def search(self, query, top_k=None, score_threshold=None):
        if not isinstance(query, str) or not query.strip():
            return []
        top_k = self.top_k if top_k is None else top_k
        threshold = self.score_threshold if score_threshold is None else score_threshold
        query_vector = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
        scores, positions = self.index.search(query_vector, min(top_k, self.index.ntotal))
        results = []
        for score, position in zip(scores[0], positions[0]):
            if position < 0 or (threshold is not None and float(score) < threshold):
                continue
            record = self.metadata[str(int(position))]
            results.append({"chunk_id": record["chunk_id"], "text": record["text"], "score": float(score), "metadata": record["metadata"]})
        return results

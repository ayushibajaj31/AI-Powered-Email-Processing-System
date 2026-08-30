"""Run the existing retrieval pipeline, then ask the configured LLM for a grounded reply."""

import logging
import re
from time import perf_counter

try:  # Supports both script execution and `src.rag.response_generator` imports.
    from .rag_pipeline import RAGPipeline
except ImportError:
    from rag_pipeline import RAGPipeline

try:
    from src.llm.llm_service import LLMService, LLMServiceError
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "llm"))
    from llm_service import LLMService, LLMServiceError  # noqa: E402

LOGGER = logging.getLogger(__name__)
INTERNAL_TERMS = [r"\bfaiss\b", r"\bembedding(?:s)?\b", r"\bvector database\b", r"\brag\b", r"\bclassifier\b"]


class ResponseGenerator:
    def __init__(self, pipeline=None, llm_service=None):
        self.pipeline = pipeline or RAGPipeline()
        self.llm_service = llm_service or LLMService()

    @staticmethod
    def validate_response(response):
        if not response or not response.strip():
            raise LLMServiceError("The LLM returned an empty response.")
        if len(response) > 2_000:
            raise LLMServiceError("The LLM response is too long for the customer-support format.")
        if any(re.search(term, response, flags=re.IGNORECASE) for term in INTERNAL_TERMS):
            raise LLMServiceError("The LLM response exposed an internal implementation term.")

    def process_email(self, subject, email_body, customer_id=None, order_id=None, product_id=None):
        pipeline_result = self.pipeline.process_email(subject, email_body, customer_id, order_id, product_id)
        start = perf_counter()
        response = self.llm_service.generate_response(
            {"subject": subject, "email_body": email_body},
            pipeline_result["predicted_category"], pipeline_result["context"],
        )
        generation_time = perf_counter() - start
        self.validate_response(response)
        sources = [{
            "chunk_id": chunk["chunk_id"], "topic": chunk["metadata"]["topic"],
            "category": chunk["metadata"]["category"], "source_file": chunk["metadata"]["source_file"],
            "score": chunk["score"],
        } for chunk in pipeline_result["retrieved_chunks"]]
        LOGGER.info("LLM response generated; category=%s; chunks=%s; seconds=%.2f", pipeline_result["predicted_category"], len(sources), generation_time)
        return {
            "predicted_category": pipeline_result["predicted_category"], "response": response, "sources": sources,
            "response_generation_time": generation_time, "classification_time": pipeline_result["classification_time"],
            "retrieval_time": pipeline_result["retrieval_time"],
        }

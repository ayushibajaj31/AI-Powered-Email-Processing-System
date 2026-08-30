"""Offline RAG integration tests against the checked-in FAISS knowledge base.

The LLM is deliberately faked: these tests verify retrieval and that only retrieved
context is passed to generation, without needing an external LLM service.
"""

import unittest
from pathlib import Path

from src.rag.rag_pipeline import RAGPipeline
from src.rag.response_generator import ResponseGenerator


class Classifier:
    def __init__(self, category): self.category = category
    def predict(self, values): return [self.category for _ in values]


class Repository:
    def get_customer(self, customer_id): return {"customer_id": customer_id, "customer_since": "2026-01-01"}
    def get_verified_order(self, customer_id, order_id): return {"order_id": order_id, "order_status": "Shipped", "payment_status": "Paid", "order_date": "2026-01-01"}
    def get_products_for_order(self, order_id): return []
    def get_product(self, product_id): return None


class RecordingLLM:
    def __init__(self): self.context = None
    def generate_response(self, email, category, context):
        self.context = context
        return "Based on the supplied company policy, support can confirm the next steps."


class RAGEndToEndTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        if not (root / "data/vector_store/faiss.index").exists():
            raise unittest.SkipTest("FAISS assets are not present.")

    def _pipeline(self, category):
        return RAGPipeline(repository=Repository(), classifier=Classifier(category))

    def test_policy_questions_return_relevant_nonempty_chunks(self):
        cases = [
            ("Return policy", "What is the return policy?", "Return/Refund", "returns"),
            ("Exchange time", "How long do I have to exchange a product?", "Exchange", "exchange"),
            ("Warranty", "What is the warranty policy?", "Product Information", "products"),
            ("Size exchange", "Can I exchange a product for another size?", "Exchange", "exchange"),
        ]
        for subject, body, category, expected_source_category in cases:
            with self.subTest(subject=subject):
                result = self._pipeline(category).process_email(subject, body)
                self.assertTrue(result["retrieved_chunks"])
                self.assertTrue(result["context"].startswith("RELEVANT COMPANY POLICY:"))
                self.assertIn(expected_source_category, {chunk["metadata"]["category"] for chunk in result["retrieved_chunks"]})

    def test_final_generator_receives_retrieved_context(self):
        llm = RecordingLLM()
        generator = ResponseGenerator(pipeline=self._pipeline("Exchange"), llm_service=llm)
        result = generator.process_email("Exchange size", "Can I exchange this for another size?")
        self.assertTrue(result["sources"])
        self.assertIn("RELEVANT COMPANY POLICY:", llm.context)
        self.assertNotIn("FAISS", result["response"])


if __name__ == "__main__":
    unittest.main()

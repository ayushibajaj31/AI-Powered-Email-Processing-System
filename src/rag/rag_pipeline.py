"""Connect email classification, structured records, and FAISS policy retrieval.

The pipeline prepares context for a future LLM but never generates a reply.
"""

import logging
import re
from pathlib import Path
from time import perf_counter

import joblib

try:  # Supports both `python src/rag/...` and package imports from FastAPI.
    from .retriever import VectorRetriever
except ImportError:
    from retriever import VectorRetriever

from src.database import database as database_module
from src.database.database import configure_database
from src.database.repositories import DatabaseRepository, RecordNotFoundError


RAG_TOP_K = 5
RAG_SCORE_THRESHOLD = None
CATEGORY_HINTS = {
    "Order Status": ("shipping order tracking delivery status", {"shipping"}),
    "Return/Refund": ("return refund eligibility process timeline", {"returns"}),
    "Exchange": ("exchange policy size color variant eligibility availability", {"exchange"}),
    "Cancellation": ("cancellation policy order before shipment", {"cancellation"}),
    "Payment Issue": ("payment failed pending duplicate charge verification", {"payments"}),
    "Product Information": ("product specifications availability sizes colors warranty", {"products"}),
    "Complaint": ("complaint damaged wrong product escalation support", {"support", "returns"}),
    "Other": ("customer support policy", set()),
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def project_root():
    return Path(__file__).resolve().parents[2]


def find_id(text, pattern):
    match = re.search(pattern, text or "", flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


class RAGPipeline:
    def __init__(self, top_k=RAG_TOP_K, score_threshold=RAG_SCORE_THRESHOLD, repository=None, retriever=None, classifier=None):
        self.top_k = top_k
        self.score_threshold = score_threshold
        root = project_root()
        self._owns_session = False
        if repository is None:
            # Structured customer, order, and product data now comes from PostgreSQL.
            # Alembic creates the schema; this code never creates tables itself.
            if database_module.SessionLocal is None:
                configure_database()
            self._session = database_module.SessionLocal()
            self.repository = DatabaseRepository(self._session)
            self._owns_session = True
        else:
            self.repository = repository
        self.classifier = classifier if classifier is not None else joblib.load(root / "models" / "email_classifier_final.pkl")
        self.retriever = retriever if retriever is not None else VectorRetriever(top_k=top_k, score_threshold=None)

    def get_customer(self, customer_id):
        return self.repository.get_customer(customer_id) if customer_id else None

    def get_order(self, order_id):
        return self.repository.get_order(order_id) if order_id else None

    def get_product(self, product_id):
        return self.repository.get_product(product_id) if product_id else None

    def extract_ids(self, text, customer_id=None, order_id=None, product_id=None):
        """Prefer caller-provided IDs, then use only explicit matching ID text."""
        return {
            "customer_id": customer_id or find_id(text, r"\bCUST\d{4}\b"),
            "order_id": order_id or find_id(text, r"\bORD\d{5}\b"),
            "product_id": product_id or find_id(text, r"\bPRD-\d{3}\b"),
        }

    def construct_retrieval_query(self, text, category, order, product):
        hint, _ = CATEGORY_HINTS.get(category, CATEGORY_HINTS["Other"])
        details = [f"Customer intent: {category}.", hint, f"Customer request: {text}"]
        if product:
            details.append(f"Product: {product['product_name']}; category: {product['category']}; available sizes: {product['available_sizes'] or 'not applicable'}; warranty: {product['warranty_period']}.")
        if order:
            details.append(f"Order status: {order['order_status']}; payment status: {order['payment_status']}.")
        return " ".join(details)

    def retrieve(self, query, category):
        """Guide ranking toward relevant policy categories without discarding others."""
        return self._retrieve_from_vector_store(query, category)

    def _retrieve_from_vector_store(self, query, category):
        """Run embedding + FAISS ranking. Retrieval logic lives only here."""
        _, preferred_categories = CATEGORY_HINTS.get(category, CATEGORY_HINTS["Other"])
        candidates = self.retriever.search(query, top_k=max(self.top_k * 3, self.top_k))
        guided = []
        for result in candidates:
            boosted_score = result["score"] + (0.08 if result["metadata"]["category"] in preferred_categories else 0.0)
            result = {**result, "score": float(boosted_score)}
            if self.score_threshold is None or result["score"] >= self.score_threshold:
                guided.append(result)
        return sorted(guided, key=lambda result: result["score"], reverse=True)[:self.top_k]

    def build_context(self, customer, order, product, retrieved_chunks):
        """Produce minimal, structured factual context for a future downstream LLM."""
        sections = []
        if customer:
            sections.append("CUSTOMER INFORMATION:\n" + "\n".join([
                f"Customer ID: {customer['customer_id']}", f"Customer Since: {customer['customer_since']}",
            ]))
        if order:
            sections.append("ORDER INFORMATION:\n" + "\n".join([
                f"Order ID: {order['order_id']}", f"Status: {order['order_status']}",
                f"Payment Status: {order['payment_status']}", f"Order Date: {order['order_date']}",
            ]))
        if product:
            sections.append("PRODUCT INFORMATION:\n" + "\n".join([
                f"Product ID: {product['product_id']}", f"Product: {product['product_name']}",
                f"Category: {product['category']}", f"Available Sizes: {product['available_sizes'] or 'Not applicable'}",
                f"Available Colors: {product['available_colors']}", f"Warranty: {product['warranty_period']}",
                f"Stock Quantity: {product['stock_quantity']}",
            ]))
        if retrieved_chunks:
            policies = []
            for number, chunk in enumerate(retrieved_chunks, start=1):
                metadata = chunk["metadata"]
                policies.append(f"[{number}] {metadata['category']} / {metadata['topic']} (score {chunk['score']:.4f})\n{chunk['text']}")
            sections.append("RELEVANT COMPANY POLICY:\n" + "\n\n".join(policies))
        if not sections:
            return "No structured records or relevant policy chunks were available."
        return "\n\n".join(sections)

    def process_email(self, subject, email_body, customer_id=None, order_id=None, product_id=None):
        if not isinstance(subject, str) or not isinstance(email_body, str) or not (subject.strip() or email_body.strip()):
            raise ValueError("Provide a non-empty subject or email body.")
        text = f"{subject.strip()} {email_body.strip()}".strip()
        classification_start = perf_counter()
        predicted_category = self.classifier.predict([text])[0]
        classification_time = perf_counter() - classification_start
        ids = self.extract_ids(text, customer_id, order_id, product_id)
        # Never retrieve an order merely because its ID appeared in an email: when an
        # order is requested, a customer ID must be present and ownership is checked
        # through the shared repository/service layer.
        if ids["order_id"]:
            if not ids["customer_id"]:
                raise ValueError("customer_id is required when order_id is provided.")
            order = self.repository.get_verified_order(ids["customer_id"], ids["order_id"])
            products = self.repository.get_products_for_order(ids["order_id"])
            product = products[0] if products else None
        else:
            order = None
            product = self.get_product(ids["product_id"])

        customer = self.get_customer(ids["customer_id"])
        if ids["customer_id"] and not customer:
            raise RecordNotFoundError("Customer was not found.")
        retrieval_query = self.construct_retrieval_query(text, predicted_category, order, product)
        retrieval_start = perf_counter()
        retrieved_chunks = self.retrieve(retrieval_query, predicted_category)
        retrieval_time = perf_counter() - retrieval_start
        LOGGER.info("Email received; category=%s; extracted_ids=%s", predicted_category, ids)
        LOGGER.info("Retrieved %s chunks: %s", len(retrieved_chunks), [(chunk['chunk_id'], round(chunk['score'], 4)) for chunk in retrieved_chunks])
        return {
            "subject": subject, "email_body": email_body, "predicted_category": predicted_category,
            "extracted_ids": ids, "customer": customer, "order": order, "product": product,
            "retrieval_query": retrieval_query, "retrieved_chunks": retrieved_chunks,
            "context": self.build_context(customer, order, product, retrieved_chunks),
            "classification_time": classification_time, "retrieval_time": retrieval_time,
        }

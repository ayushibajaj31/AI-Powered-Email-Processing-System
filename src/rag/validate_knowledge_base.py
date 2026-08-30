"""Validate the generated Northstar Market knowledge-base documents and metadata."""

import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = {"document_id", "file_name", "category", "topic", "source", "version"}
REQUIRED_TOPICS = {"order_processing", "order_tracking", "shipping_policy", "delivery_issues", "return_policy", "refund_policy", "damaged_wrong_products", "exchange_policy", "exchange_process", "exchange_availability", "cancellation_policy", "payment_methods", "payment_issues", "product_information", "warranty", "customer_support", "complaint_handling", "escalation_policy", "frequently_asked_questions"}


def project_root():
    return Path(__file__).resolve().parents[2]


def find_contradictions(documents):
    """Check the expected core policy values in their authoritative documents."""
    expectations = {
        "returns/return_policy.txt": "30 calendar days",
        "exchange/exchange_policy.txt": "30 calendar days",
        "shipping/order_processing.txt": "1-2 business days",
        "shipping/shipping_policy.txt": "3-5 business days",
        "returns/refund_policy.txt": "5-7 business days",
        "cancellation/cancellation_policy.txt": "5-7 business days",
    }
    failures = []
    for file_name, expected_text in expectations.items():
        if expected_text not in documents.get(file_name, ""):
            failures.append(f"Expected '{expected_text}' in {file_name}")
    return failures


def validate_knowledge_base(knowledge_base):
    metadata_path = knowledge_base / "metadata.json"
    if not metadata_path.exists():
        return {"error": "metadata.json is missing"}
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    documents, empty, hashes, missing_metadata = {}, [], {}, []
    for entry in metadata:
        missing_fields = REQUIRED_FIELDS - set(entry)
        if missing_fields or any(not str(entry.get(field, "")).strip() for field in REQUIRED_FIELDS):
            missing_metadata.append(entry.get("file_name", "unknown"))
            continue
        path = knowledge_base / entry["file_name"]
        if not path.exists():
            empty.append(entry["file_name"])
            continue
        content = path.read_text(encoding="utf-8").strip()
        documents[entry["file_name"]] = content
        if not content:
            empty.append(entry["file_name"])
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        hashes.setdefault(digest, []).append(entry["file_name"])
    duplicates = [names for names in hashes.values() if len(names) > 1]
    missing_topics = sorted(REQUIRED_TOPICS - {entry.get("topic") for entry in metadata})
    short_documents = [name for name, content in documents.items() if len(content) < 80]
    return {
        "document_count": len(metadata), "empty_documents": empty, "duplicate_documents": duplicates,
        "missing_metadata": missing_metadata, "missing_topics": missing_topics,
        "short_documents_under_80_characters": short_documents,
        "missing_categories": [entry.get("file_name", "unknown") for entry in metadata if not entry.get("category")],
        "missing_source": [entry.get("file_name", "unknown") for entry in metadata if not entry.get("source")],
        "missing_version": [entry.get("file_name", "unknown") for entry in metadata if not entry.get("version")],
        "contradiction_checks": find_contradictions(documents),
    }


def write_report(path, results):
    lines = ["KNOWLEDGE BASE VALIDATION REPORT", "=" * 60]
    if "error" in results:
        lines.extend(["", f"ERROR: {results['error']}"])
    else:
        lines.extend(["", f"Number of documents: {results['document_count']}"])
        for key, value in results.items():
            if key == "document_count":
                continue
            lines.append(f"{key.replace('_', ' ').title()}: {value if value else 'None'}")
        passed = all(not value for key, value in results.items() if key != "document_count")
        lines.extend(["", "Final status: PASSED" if passed else "Final status: FAILED — review findings above."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    knowledge_base = project_root() / "data" / "knowledge_base"
    results = validate_knowledge_base(knowledge_base)
    write_report(knowledge_base / "knowledge_base_report.txt", results)
    if "error" in results:
        print(f"Knowledge base validation failed: {results['error']}")
        return
    passed = all(not value for key, value in results.items() if key != "document_count")
    print(f"Knowledge-base documents: {results['document_count']}")
    print(f"Validation status: {'PASSED' if passed else 'FAILED'}")
    print(f"Report: {knowledge_base / 'knowledge_base_report.txt'}")


if __name__ == "__main__":
    main()

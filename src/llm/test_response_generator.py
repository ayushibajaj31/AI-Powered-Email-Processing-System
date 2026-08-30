"""Run required grounded-response and missing-information test cases."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))
from response_generator import ResponseGenerator
from llm_service import LLMServiceError


TESTS = [
    ("Order Status", "Where is my order?", "I ordered my shoes five days ago."),
    ("Exchange", "Need size 9", "I received size 8 but I need size 9. Can I exchange it?"),
    ("Return/Refund", "Return request", "I don't want this product anymore. How can I return it and get a refund?"),
    ("Cancellation", "Cancel order", "I placed the order by mistake. Can I cancel it?"),
    ("Payment", "Duplicate charge", "I was charged twice for the same order."),
    ("Product Information", "Product details", "What sizes are available for this shoe and what warranty does it have?"),
    ("Missing Information", "Loyalty program", "What is your loyalty program and how many points do I earn?"),
]


def main():
    tests = []
    output = Path(__file__).resolve().parents[2] / "data" / "evaluation"
    output.mkdir(parents=True, exist_ok=True)
    try:
        generator = ResponseGenerator()
    except LLMServiceError as error:
        print(f"Cannot run LLM tests: {error}")
        for expected, subject, body in TESTS:
            tests.append({"expected_area": expected, "input_email": {"subject": subject, "email_body": body}, "test_status": "not_run", "error": str(error)})
        (output / "llm_response_tests.json").write_text(json.dumps(tests, indent=2) + "\n", encoding="utf-8")
        return
    for expected, subject, body in TESTS:
        item = {"expected_area": expected, "input_email": {"subject": subject, "email_body": body}}
        try:
            result = generator.process_email(subject, body)
            item.update({"predicted_category": result["predicted_category"], "retrieved_sources": result["sources"], "generated_response": result["response"], "response_generation_time": result["response_generation_time"], "test_status": "completed"})
            print(f"{expected}: {result['predicted_category']}\n{result['response']}\n")
        except LLMServiceError as error:
            item.update({"test_status": "failed", "error": str(error)})
            print(f"{expected}: failed — {error}")
        tests.append(item)
    (output / "llm_response_tests.json").write_text(json.dumps(tests, indent=2) + "\n", encoding="utf-8")
    print(f"Saved results: {output / 'llm_response_tests.json'}")

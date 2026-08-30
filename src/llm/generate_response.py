"""Manual command-line entry point for the full classification-to-response flow."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))
from response_generator import ResponseGenerator  # noqa: E402
from llm_service import LLMServiceError


def main():
    parser = argparse.ArgumentParser(description="Generate a grounded Northstar Market customer-support response.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--customer-id")
    parser.add_argument("--order-id")
    parser.add_argument("--product-id")
    args = parser.parse_args()
    try:
        result = ResponseGenerator().process_email(args.subject, args.body, args.customer_id, args.order_id, args.product_id)
    except LLMServiceError as error:
        print(f"Response generation failed: {error}")
        return
    print(f"Predicted Category: {result['predicted_category']}")
    print("Retrieved Sources:")
    for source in result["sources"]:
        print(f"- {source['chunk_id']} | {source['topic']} | score {source['score']:.4f}")
    print("Generated Response:")
    print(result["response"])


if __name__ == "__main__":
    main()

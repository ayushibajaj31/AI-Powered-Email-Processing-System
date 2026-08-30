"""Exercise the Step 10 pipeline without generating customer responses."""

from rag_pipeline import RAGPipeline


TEST_CASES = [
    ("Order Status", "Where is my order?", "I ordered my shoes five days ago and want to know the current status."),
    ("Exchange", "Need a different size", "I received the shoes but size 8 is too small. Can I exchange them for size 9?"),
    ("Return/Refund", "Want to return my product", "The product isn't suitable for me. How can I return it and get my money back?"),
    ("Cancellation", "Cancel order", "I placed this order by mistake. Can I cancel it?"),
    ("Payment Issue", "Payment deducted twice", "I was charged two times for the same order."),
    ("Product Information", "Product details", "Can you tell me the warranty and available sizes for this shoe?"),
    ("Complaint", "Damaged product", "The product I received is damaged. What should I do?"),
]


def main():
    pipeline = RAGPipeline()
    # Use one real order in selected cases to show trustworthy order -> product lookup.
    sample_order = pipeline.orders.iloc[0].to_dict()
    for number, (expected, subject, body) in enumerate(TEST_CASES, start=1):
        use_order = number in {2, 4, 6}
        result = pipeline.process_email(subject, body, order_id=sample_order["order_id"] if use_order else None)
        print("=" * 60)
        print(f"CASE {number} — expected: {expected}")
        print(f"Customer Email: {subject}\n{body}")
        print(f"Predicted Category: {result['predicted_category']}")
        print(f"Customer: {result['customer']}")
        print(f"Order: {result['order']}")
        print(f"Product: {result['product']}")
        print("Retrieved Knowledge:")
        for chunk_number, chunk in enumerate(result["retrieved_chunks"], start=1):
            metadata = chunk["metadata"]
            print(f"{chunk_number}. Score: {chunk['score']:.4f} | {metadata['category']} / {metadata['topic']}\n{chunk['text']}")
        print(f"Context:\n{result['context']}")


if __name__ == "__main__":
    main()

"""Run manual semantic retrieval checks, including top-k comparison."""

from pathlib import Path

from retriever import VectorRetriever


TESTS = [
    ("Where is my order?", "shipping / order tracking"),
    ("Can I exchange my shoes for another size?", "exchange"),
    ("How long will it take to get my refund?", "refund"),
    ("I want to cancel my order.", "cancellation"),
    ("My payment failed.", "payment"),
    ("What warranty does the product have?", "warranty / product"),
    ("I received a damaged product.", "damaged products / returns / complaint"),
]


def project_root():
    return Path(__file__).resolve().parents[2]


def format_results(results):
    lines = []
    for number, result in enumerate(results, start=1):
        metadata = result["metadata"]
        lines.extend([f"Result {number}: {result['chunk_id']}", f"Score: {result['score']:.4f}", f"Category: {metadata['category']}", f"Topic: {metadata['topic']}", f"Text: {result['text']}"])
    return lines


def main():
    retriever = VectorRetriever(top_k=5)
    report = ["RETRIEVAL TEST RESULTS", "=" * 60]
    for query, expected in TESTS:
        results = retriever.search(query)
        retrieved_topics = [result["metadata"]["topic"] for result in results]
        relevant = any(token in " ".join(retrieved_topics + [result["metadata"]["category"] for result in results]).casefold() for token in expected.replace("/", " ").split())
        section = ["", f"Query: {query}", f"Expected relevant area: {expected}", *format_results(results), f"Appears relevant: {'Yes' if relevant else 'No'}"]
        print("\n".join(section))
        report.extend(section)
    report.extend(["", "TOP-K EXPERIMENT", "Smaller top_k returns less context and fewer irrelevant chunks; larger top_k provides broader context but may add noise and later LLM tokens."])
    query = "Can I exchange my shoes for another size?"
    for top_k in (1, 3, 5):
        results = retriever.search(query, top_k=top_k)
        report.append(f"top_k={top_k}: {[result['chunk_id'] for result in results]}")
    path = project_root() / "data" / "vector_store" / "retrieval_test_results.txt"
    path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nSaved retrieval review: {path}")


if __name__ == "__main__":
    main()

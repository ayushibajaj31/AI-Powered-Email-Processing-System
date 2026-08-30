"""Train and evaluate a baseline TF-IDF + Logistic Regression email classifier."""

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report,
                             precision_recall_fscore_support)
from sklearn.pipeline import Pipeline


RANDOM_STATE = 42
CATEGORIES = [
    "Order Status", "Return/Refund", "Cancellation", "Payment Issue",
    "Product Information", "Complaint", "Exchange", "Other",
]


def project_root():
    return Path(__file__).resolve().parents[2]


def load_split(path):
    """Load one already-prepared split and reject missing model inputs."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"text", "category"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{path.name} must contain: {sorted(required)}")
    if frame["text"].str.strip().eq("").any() or frame["category"].str.strip().eq("").any():
        raise ValueError(f"{path.name} has empty text or category values. Fix Step 3 first.")
    return frame


def build_pipeline():
    """Use word unigrams/bigrams and a simple, reproducible linear baseline."""
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
        )),
        ("classifier", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])


def evaluate_model(model, frame):
    """Return metrics, predictions, and a detailed per-class report."""
    actual = frame["category"]
    predicted = model.predict(frame["text"])
    macro = precision_recall_fscore_support(actual, predicted, labels=CATEGORIES, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(actual, predicted, labels=CATEGORIES, average="weighted", zero_division=0)
    metrics = {
        "accuracy": accuracy_score(actual, predicted),
        "macro_precision": macro[0], "macro_recall": macro[1], "macro_f1": macro[2],
        "weighted_precision": weighted[0], "weighted_recall": weighted[1], "weighted_f1": weighted[2],
    }
    report = classification_report(actual, predicted, labels=CATEGORIES, zero_division=0)
    return metrics, predicted, report


def save_confusion_matrix(actual, predicted, output_path):
    figure, axis = plt.subplots(figsize=(10, 8))
    display = ConfusionMatrixDisplay.from_predictions(
        actual, predicted, labels=CATEGORIES, xticks_rotation=40, cmap="Blues", colorbar=False, ax=axis
    )
    display.ax_.set_title("Baseline Classifier Confusion Matrix — Test Set")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def demo_predictions(model):
    """Use manually written examples to demonstrate end-to-end predictions."""
    examples = [
        ("Where is my parcel?", "I ordered last week and tracking has not moved."),
        ("Return request", "The shoes are too small. I want to return them."),
        ("Cancel this please", "I placed the order by accident and need to cancel it."),
        ("Payment was deducted twice", "My card shows two charges for one purchase."),
        ("Question about colors", "Do you have this backpack in blue or green?"),
        ("Damaged item", "The lamp arrived broken and the box was crushed."),
        ("Need smaller size", "I ordered M size but I need S size. I would like an exchange."),
        ("Password help", "I cannot sign in to my account after resetting my password."),
        ("order still processing", "hey, why has my package not shipped yet??"),
        ("Need help", "I got something but it is not right. What should I do?"),
        ("Warranty", "How long is the warranty for these headphones?"),
    ]
    texts = [f"{subject} {body}" for subject, body in examples]
    probabilities = model.predict_proba(texts)
    predicted = model.classes_[probabilities.argmax(axis=1)]
    return [(text, label, float(probability.max())) for text, label, probability in zip(texts, predicted, probabilities)]


def format_metrics(metrics):
    return "\n".join(f"{name.replace('_', ' ').title()}: {value:.4f}" for name, value in metrics.items())


def save_results(path, validation_metrics, validation_report, test_metrics, test_report, demos):
    lines = ["BASELINE EMAIL CLASSIFICATION RESULTS", "=" * 60, "", "MODEL", "TF-IDF (unigrams and bigrams) + Logistic Regression", "", "VALIDATION METRICS", format_metrics(validation_metrics), "", "VALIDATION CLASSIFICATION REPORT", validation_report, "", "TEST METRICS", format_metrics(test_metrics), "", "TEST CLASSIFICATION REPORT", test_report, "", "MANUAL EXAMPLE PREDICTIONS"]
    for text, label, confidence in demos:
        lines.extend([f"Email: {text}", f"Predicted category: {label}", f"Confidence: {confidence:.2f}", ""])
    lines.append("Note: Test metrics are reported for final evaluation only and were not used to tune this baseline.")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    root = project_root()
    processed, models = root / "data" / "processed", root / "models"
    train = load_split(processed / "train.csv")
    validation = load_split(processed / "validation.csv")
    test = load_split(processed / "test.csv")

    model = build_pipeline()
    # Calling fit here learns vocabulary and IDF values from train only.
    model.fit(train["text"], train["category"])

    validation_metrics, _, validation_report = evaluate_model(model, validation)
    test_metrics, test_predictions, test_report = evaluate_model(model, test)
    demos = demo_predictions(model)

    models.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, models / "email_classifier.pkl")
    save_confusion_matrix(test["category"], test_predictions, processed / "plots" / "confusion_matrix.png")
    save_results(processed / "classification_results.txt", validation_metrics, validation_report, test_metrics, test_report, demos)

    print("Baseline training complete.")
    print(f"Validation accuracy: {validation_metrics['accuracy']:.4f} | macro F1: {validation_metrics['macro_f1']:.4f}")
    print(f"Test accuracy: {test_metrics['accuracy']:.4f} | macro F1: {test_metrics['macro_f1']:.4f}")
    print(f"Saved model: {models / 'email_classifier.pkl'}")
    print(f"Saved results: {processed / 'classification_results.txt'}")
    print("Manual predictions:")
    for text, label, confidence in demos:
        print(f"  {label} ({confidence:.2f}) — {text}")


if __name__ == "__main__":
    main()

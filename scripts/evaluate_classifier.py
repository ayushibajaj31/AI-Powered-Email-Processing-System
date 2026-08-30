"""Evaluate the existing saved classifier; this script never trains a model."""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support


ROOT = Path(__file__).resolve().parents[1]


def main():
    dataset = pd.read_csv(ROOT / "data" / "processed" / "test.csv")
    model = joblib.load(ROOT / "models" / "email_classifier_final.pkl")
    expected = dataset["category"].astype(str)
    predicted = model.predict(dataset["text"].fillna("").astype(str))
    labels = sorted(set(expected) | set(predicted))
    precision, recall, f1, support = precision_recall_fscore_support(expected, predicted, labels=labels, zero_division=0)
    report = {
        "dataset": str(ROOT / "data" / "processed" / "test.csv"), "emails": len(dataset),
        "accuracy": float(accuracy_score(expected, predicted)),
        "macro_precision": float(precision_recall_fscore_support(expected, predicted, average="macro", zero_division=0)[0]),
        "macro_recall": float(precision_recall_fscore_support(expected, predicted, average="macro", zero_division=0)[1]),
        "macro_f1": float(precision_recall_fscore_support(expected, predicted, average="macro", zero_division=0)[2]),
        "per_category": [{"category": label, "number_of_emails": int(count), "correct_predictions": int(((expected == label) & (predicted == label)).sum()), "incorrect_predictions": int(((expected == label) & (predicted != label)).sum()), "accuracy": float(((expected == label) & (predicted == label)).sum() / count) if count else 0.0, "precision": float(p), "recall": float(r), "f1_score": float(score)} for label, p, r, score, count in zip(labels, precision, recall, f1, support)],
        "labels": labels, "confusion_matrix": confusion_matrix(expected, predicted, labels=labels).tolist(),
    }
    output = ROOT / "reports" / "classifier_evaluation.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Classifier evaluation: {len(dataset)} emails")
    print(f"Accuracy: {report['accuracy']:.4f}  Macro precision/recall/F1: {report['macro_precision']:.4f}/{report['macro_recall']:.4f}/{report['macro_f1']:.4f}")
    for item in report["per_category"]:
        print("{category}: {correct_predictions}/{number_of_emails} correct, accuracy={accuracy:.4f}, F1={f1_score:.4f}".format(**item))
    print(f"Confusion matrix labels: {', '.join(labels)}")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()

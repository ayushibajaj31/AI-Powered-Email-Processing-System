"""Predict an email category using the saved baseline classification pipeline."""

import argparse
from pathlib import Path

import joblib


def project_root():
    return Path(__file__).resolve().parents[2]


def predict_email(subject, body):
    model_path = project_root() / "models" / "email_classifier_final.pkl"
    if not model_path.exists():
        raise FileNotFoundError("Model not found. Run src/ml/train_classifier.py first.")
    text = f"{subject.strip()} {body.strip()}".strip()
    if not text:
        raise ValueError("Provide a non-empty subject or email body.")
    model = joblib.load(model_path)
    category = model.predict([text])[0]
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba([text])[0]
        return category, float(probabilities.max())
    return category, None


def run_demo():
    examples = [
        ("Package update", "Where is my order? The tracking has not changed."),
        ("Return item", "I want to send these shoes back for a refund."),
        ("Cancel order", "Please cancel my order; I ordered by mistake."),
        ("Payment issue", "Why was I charged twice for one order?"),
        ("Product colors", "Is this bottle available in green?"),
        ("Broken product", "My speaker arrived damaged and does not work."),
        ("Size exchange", "I need to swap medium for small, not return it."),
        ("Account access", "I forgot my password and cannot log in."),
        ("help with order", "my delivery is late pls check"),
        ("Warranty question", "What warranty comes with the headphones?"),
    ]
    for subject, body in examples:
        category, confidence = predict_email(subject, body)
        print(f"Subject: {subject}\nEmail body: {body}\nPredicted category: {category}")
        print(f"Confidence: {confidence:.2f}" if confidence is not None else "Confidence probability: unavailable for this model")
        print()


def main():
    parser = argparse.ArgumentParser(description="Predict an e-commerce email category.")
    parser.add_argument("--subject", default="", help="Email subject")
    parser.add_argument("--body", default="", help="Email body")
    parser.add_argument("--demo", action="store_true", help="Run ten manually written example emails")
    args = parser.parse_args()
    if args.demo:
        run_demo()
        return
    category, confidence = predict_email(args.subject, args.body)
    print(f"Predicted category: {category}")
    print(f"Confidence: {confidence:.2f}" if confidence is not None else "Confidence probability: unavailable for this model")


if __name__ == "__main__":
    main()

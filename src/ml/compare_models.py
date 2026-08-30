"""Compare classical TF-IDF email classifiers and select a final model."""

from pathlib import Path
from time import perf_counter

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report,
                             precision_recall_fscore_support)
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


RANDOM_STATE = 42
CATEGORIES = ["Order Status", "Return/Refund", "Cancellation", "Payment Issue", "Product Information", "Complaint", "Exchange", "Other"]


def project_root():
    return Path(__file__).resolve().parents[2]


def load_split(path):
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if {"text", "category"} - set(frame.columns):
        raise ValueError(f"{path.name} must contain text and category columns.")
    if frame["text"].str.strip().eq("").any() or frame["category"].str.strip().eq("").any():
        raise ValueError(f"{path.name} contains empty text or category values.")
    return frame


def tfidf_vectorizer():
    """The same vectorizer configuration is used for every comparison model."""
    return TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2), min_df=2, max_df=0.95)


def build_models():
    return {
        "Logistic Regression": Pipeline([
            ("tfidf", tfidf_vectorizer()),
            ("classifier", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
        ]),
        "Linear SVM": Pipeline([
            ("tfidf", tfidf_vectorizer()),
            ("classifier", LinearSVC(random_state=RANDOM_STATE, dual=True)),
        ]),
        "Multinomial Naive Bayes": Pipeline([
            ("tfidf", tfidf_vectorizer()),
            ("classifier", MultinomialNB()),
        ]),
    }


def calculate_metrics(actual, predicted):
    macro = precision_recall_fscore_support(actual, predicted, labels=CATEGORIES, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(actual, predicted, labels=CATEGORIES, average="weighted", zero_division=0)
    return {
        "accuracy": accuracy_score(actual, predicted),
        "macro_precision": macro[0], "macro_recall": macro[1], "macro_f1": macro[2],
        "weighted_precision": weighted[0], "weighted_recall": weighted[1], "weighted_f1": weighted[2],
    }


def train_and_evaluate(model, train, validation):
    start = perf_counter()
    model.fit(train["text"], train["category"])
    training_time = perf_counter() - start
    start = perf_counter()
    predicted = model.predict(validation["text"])
    inference_time = perf_counter() - start
    metrics = calculate_metrics(validation["category"], predicted)
    metrics["training_time"] = training_time
    metrics["inference_time"] = inference_time
    return metrics


def select_best_model(results):
    """Rank validation performance, avoiding unstable millisecond-level tie breaks."""
    simplicity = {"Multinomial Naive Bayes": 0, "Logistic Regression": 1, "Linear SVM": 2}
    ranking = results.assign(
        # At this small scale, tiny timing differences are normal measurement noise.
        _rounded_inference_time=results["inference_time"].round(2),
        _simplicity=results["model"].map(simplicity),
    )
    ordered = ranking.sort_values(
        by=["macro_f1", "weighted_f1", "accuracy", "_rounded_inference_time", "_simplicity"],
        ascending=[False, False, False, True, True],
        kind="stable",
    )
    return ordered.iloc[0]["model"], ordered.drop(columns=["_rounded_inference_time", "_simplicity"])


def evaluate_final_model(model, test):
    predicted = model.predict(test["text"])
    metrics = calculate_metrics(test["category"], predicted)
    report = classification_report(test["category"], predicted, labels=CATEGORIES, zero_division=0)
    return metrics, predicted, report


def save_confusion_matrix(actual, predicted, path, model_name):
    figure, axis = plt.subplots(figsize=(10, 8))
    ConfusionMatrixDisplay.from_predictions(actual, predicted, labels=CATEGORIES, xticks_rotation=40, cmap="Blues", colorbar=False, ax=axis)
    axis.set_title(f"Final Model Confusion Matrix — {model_name}")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def save_comparison_plot(results, path):
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.bar(results["model"], results["macro_f1"], color=["#4C78A8", "#F28E2B", "#59A14F"])
    axis.set_title("Validation Macro F1 by Model")
    axis.set_xlabel("Model")
    axis.set_ylabel("Macro F1")
    axis.set_ylim(0, 1.05)
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def format_metrics(metrics):
    return "\n".join(f"{key.replace('_', ' ').title()}: {value:.4f}" for key, value in metrics.items())


def save_selection_report(path, results, selected_name, test_metrics, test_report):
    lines = ["MODEL SELECTION REPORT", "=" * 60, "", "MODELS TESTED", "- TF-IDF + Logistic Regression", "- TF-IDF + Linear SVM", "- TF-IDF + Multinomial Naive Bayes", "", "VALIDATION RESULTS", results.to_string(index=False, float_format=lambda value: f"{value:.4f}"), "", "SELECTED MODEL", selected_name, "", "SELECTION REASON", "Models were ranked using validation Macro F1, then weighted F1, accuracy, and lower inference time. Millisecond-level timing differences are rounded for stable tie handling; when quality and practical speed are tied, the simpler Naive Bayes model is preferred. Macro F1 gives every email category equal importance.", "", "FINAL TEST RESULTS (selected model only)", format_metrics(test_metrics), "", "FINAL TEST CLASSIFICATION REPORT", test_report, "", "LIMITATIONS", "The data is synthetic and template-driven, so these results may be more optimistic than performance on real customer emails. The test result was not used to select a model."]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    root = project_root()
    processed, models_directory = root / "data" / "processed", root / "models"
    train = load_split(processed / "train.csv")
    validation = load_split(processed / "validation.csv")
    test = load_split(processed / "test.csv")

    rows = []
    candidates = build_models()
    for name, model in candidates.items():
        metrics = train_and_evaluate(model, train, validation)
        rows.append({"model": name, **metrics})
    results = pd.DataFrame(rows)
    selected_name, ranked_results = select_best_model(results)

    # The final evaluation is run only for the validation-selected model.
    final_model = build_models()[selected_name]
    final_model.fit(train["text"], train["category"])
    test_metrics, test_predictions, test_report = evaluate_final_model(final_model, test)

    models_directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, models_directory / "email_classifier_final.pkl")
    results.to_csv(processed / "model_comparison_results.csv", index=False)
    save_selection_report(processed / "model_selection_report.txt", ranked_results, selected_name, test_metrics, test_report)
    save_confusion_matrix(test["category"], test_predictions, processed / "plots" / "confusion_matrix.png", selected_name)
    save_comparison_plot(results, processed / "plots" / "model_comparison.png")

    print("Model comparison complete.")
    print(ranked_results[["model", "accuracy", "macro_f1", "weighted_f1", "training_time", "inference_time"]].to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"Selected model: {selected_name}")
    print(f"Final test macro F1: {test_metrics['macro_f1']:.4f}")
    print(f"Saved final model: {models_directory / 'email_classifier_final.pkl'}")


if __name__ == "__main__":
    main()

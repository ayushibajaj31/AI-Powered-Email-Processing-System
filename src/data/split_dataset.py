"""Create reproducible, stratified train/validation/test splits for email classification."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import train_test_split


RANDOM_STATE = 42
VALID_CATEGORIES = [
    "Order Status", "Return/Refund", "Cancellation", "Payment Issue",
    "Product Information", "Complaint", "Exchange", "Other",
]
REQUIRED_COLUMNS = [
    "email_id", "customer_id", "subject", "email_body", "timestamp",
    "category", "order_id", "text",
]


def project_root():
    return Path(__file__).resolve().parents[2]


def load_email_data(path):
    """Load processed emails without changing the source file."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def create_text_column(emails):
    """Create the future classifier input while retaining subject and body columns."""
    subject = emails["subject"].fillna("").astype(str).str.strip()
    body = emails["email_body"].fillna("").astype(str).str.strip()
    emails = emails.copy()
    emails["text"] = (subject + " " + body).str.replace(r"\s+", " ", regex=True).str.strip()
    return emails


def split_dataset(emails):
    """Create a 70/15/15 stratified split with a fixed random state."""
    train, temporary = train_test_split(
        emails, test_size=0.30, stratify=emails["category"], random_state=RANDOM_STATE
    )
    validation, test = train_test_split(
        temporary, test_size=0.50, stratify=temporary["category"], random_state=RANDOM_STATE
    )
    return train.copy(), validation.copy(), test.copy()


def intersection_count(left, right, column):
    return len(set(left[column]) & set(right[column]))


def check_data_leakage(train, validation, test):
    """Report overlap across splits. Customer overlap is informative, not an error."""
    pairs = [("train_validation", train, validation), ("train_test", train, test), ("validation_test", validation, test)]
    checks = {}
    for label, left, right in pairs:
        checks[f"email_id_{label}"] = intersection_count(left, right, "email_id")
        checks[f"email_body_{label}"] = intersection_count(left, right, "email_body")
        checks[f"text_{label}"] = intersection_count(left, right, "text")
        checks[f"customer_{label}"] = intersection_count(left, right, "customer_id")
    return checks


def check_class_distribution(splits):
    rows = []
    for split_name, frame in splits.items():
        counts = frame["category"].value_counts()
        for category in VALID_CATEGORIES:
            count = int(counts.get(category, 0))
            rows.append({"category": category, "split": split_name, "count": count, "percentage": round(count / len(frame) * 100, 2)})
    return pd.DataFrame(rows)


def validate_split(frame):
    """Return quality checks; findings are reported rather than silently removed."""
    return {
        "missing_text": int(frame["text"].isna().sum()),
        "empty_text": int(frame["text"].fillna("").str.strip().eq("").sum()),
        "missing_category": int(frame["category"].isna().sum() + frame["category"].fillna("").str.strip().eq("").sum()),
        "invalid_category": int((~frame["category"].isin(VALID_CATEGORIES)).sum()),
        "duplicate_email_id": int(frame["email_id"].duplicated(keep=False).sum()),
        "duplicate_text": int(frame["text"].duplicated(keep=False).sum()),
    }


def save_splits(processed_directory, train, validation, test):
    processed_directory.mkdir(parents=True, exist_ok=True)
    for filename, frame in [("train.csv", train), ("validation.csv", validation), ("test.csv", test)]:
        frame[REQUIRED_COLUMNS].to_csv(processed_directory / filename, index=False)


def create_visualization(distribution, output_path):
    pivot = distribution.pivot(index="category", columns="split", values="count").reindex(VALID_CATEGORIES)
    pivot = pivot[["Train", "Validation", "Test"]]
    axis = pivot.plot(kind="bar", figsize=(10, 5), color=["#4C78A8", "#F28E2B", "#59A14F"])
    axis.set_title("Email Category Distribution by Dataset Split")
    axis.set_xlabel("Category")
    axis.set_ylabel("Number of Emails")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def generate_split_report(path, original_count, splits, distribution, leakage, quality):
    lines = ["DATASET SPLIT REPORT", "=" * 60, "", "DATASET SUMMARY", f"Original number of emails: {original_count}"]
    for name, frame in splits.items():
        lines.append(f"{name} samples: {len(frame)}")
    lines.extend(["", "CLASS DISTRIBUTION", "Category | Train | Validation | Test"])
    table = distribution.pivot(index="category", columns="split", values="count").reindex(VALID_CATEGORIES).fillna(0).astype(int)
    for category, row in table.iterrows():
        lines.append(f"{category} | {row['Train']} | {row['Validation']} | {row['Test']}")
    lines.extend(["", "Class percentages"])
    for split_name in ["Train", "Validation", "Test"]:
        values = distribution[distribution["split"] == split_name]
        lines.append(f"{split_name}: " + ", ".join(f"{row.category} {row.percentage}%" for row in values.itertuples()))
    lines.extend(["", "LEAKAGE CHECKS (all email ID/body/text values must be zero across splits)"])
    for key, value in leakage.items():
        note = " (customer overlap is allowed)" if key.startswith("customer_") else ""
        lines.append(f"{key.replace('_', ' ').title()}: {value}{note}")
    lines.extend(["", "DATA QUALITY"])
    for name, checks in quality.items():
        lines.append(name.upper())
        lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in checks.items())
    blocking_leakage = sum(value for key, value in leakage.items() if not key.startswith("customer_"))
    blocking_quality = sum(value for checks in quality.values() for value in checks.values())
    conclusion = "Dataset split passed" if blocking_leakage == 0 and blocking_quality == 0 else "Dataset split failed: review leakage or data-quality findings above."
    lines.extend(["", "FINAL CONCLUSION", conclusion])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    root = project_root()
    processed = root / "data" / "processed"
    emails = create_text_column(load_email_data(processed / "emails_cleaned.csv"))
    train, validation, test = split_dataset(emails)
    splits = {"Train": train, "Validation": validation, "Test": test}
    leakage = check_data_leakage(train, validation, test)
    distribution = check_class_distribution(splits)
    quality = {name: validate_split(frame) for name, frame in splits.items()}
    save_splits(processed, train, validation, test)
    create_visualization(distribution, processed / "plots" / "dataset_split_distribution.png")
    generate_split_report(processed / "split_report.txt", len(emails), splits, distribution, leakage, quality)

    print("Dataset split complete.")
    print(f"Train: {len(train)} | Validation: {len(validation)} | Test: {len(test)}")
    print(f"Cross-split duplicate text: {sum(value for key, value in leakage.items() if key.startswith('text_'))}")
    print(f"Report: {processed / 'split_report.txt'}")


if __name__ == "__main__":
    main()

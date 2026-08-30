"""Create Step 2 charts from the cleaned e-commerce datasets."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main():
    root = Path(__file__).resolve().parents[2]
    processed = root / "data" / "processed"
    plots = processed / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    emails = pd.read_csv(processed / "emails_cleaned.csv", dtype=str, keep_default_na=False)
    orders = pd.read_csv(processed / "orders_cleaned.csv", dtype=str, keep_default_na=False)

    counts = emails["category"].value_counts().sort_index()
    plt.figure(figsize=(10, 5))
    counts.plot(kind="bar", color="#4C78A8")
    plt.title("Emails per Category")
    plt.xlabel("Category")
    plt.ylabel("Number of Emails")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(plots / "emails_per_category.png", dpi=150)
    plt.close()

    lengths = emails["email_body"].str.len()
    plt.figure(figsize=(8, 5))
    plt.hist(lengths, bins=20, color="#59A14F", edgecolor="white")
    plt.title("Distribution of Email Lengths")
    plt.xlabel("Characters in Email Body")
    plt.ylabel("Number of Emails")
    plt.tight_layout()
    plt.savefig(plots / "email_length_distribution.png", dpi=150)
    plt.close()

    customer_order_counts = orders.groupby("customer_id").size()
    plt.figure(figsize=(8, 5))
    plt.hist(customer_order_counts, bins=range(1, int(customer_order_counts.max()) + 2), align="left", color="#F28E2B", edgecolor="white")
    plt.title("Orders per Customer")
    plt.xlabel("Orders")
    plt.ylabel("Number of Customers")
    plt.tight_layout()
    plt.savefig(plots / "orders_per_customer.png", dpi=150)
    plt.close()
    print(f"Saved plots to: {plots}")


if __name__ == "__main__":
    main()

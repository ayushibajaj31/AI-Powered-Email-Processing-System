"""Clean, validate, and prepare the synthetic e-commerce CSV datasets.

Raw files are never changed. Invalid or incomplete records are reported rather
than silently discarded; only exact duplicate rows are removed.
"""

from collections import Counter
from pathlib import Path
import re

import pandas as pd


VALID_CATEGORIES = [
    "Order Status", "Return/Refund", "Cancellation", "Payment Issue",
    "Product Information", "Complaint", "Exchange", "Other",
]
VALID_ORDER_STATUSES = {"Processing", "Shipped", "Out for Delivery", "Delivered", "Cancelled", "Returned"}
VALID_PAYMENT_STATUSES = {"Paid", "Pending", "Failed", "Refunded"}
CATEGORY_LOOKUP = {re.sub(r"\s+", " ", value).casefold(): value for value in VALID_CATEGORIES}


def project_root():
    return Path(__file__).resolve().parents[2]


def load_data(raw_directory):
    """Load CSV columns as text so IDs and empty optional fields are preserved."""
    read_options = {"dtype": str, "keep_default_na": False}
    return (
        pd.read_csv(raw_directory / "customers.csv", **read_options),
        pd.read_csv(raw_directory / "products.csv", **read_options),
        pd.read_csv(raw_directory / "orders.csv", **read_options),
        pd.read_csv(raw_directory / "emails.csv", **read_options),
    )


def blank_count(frame, columns=None):
    columns = columns or frame.columns
    return int(sum(frame[column].astype(str).str.strip().eq("").sum() for column in columns))


def invalid_date_count(series):
    present = series.astype(str).str.strip().ne("")
    return int(pd.to_datetime(series.where(present), errors="coerce").isna().sum() - (~present).sum())


def validate_customers(customers):
    email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return {
        "duplicate_customer_id": int(customers["customer_id"].duplicated(keep=False).sum()),
        "duplicate_email_address": int(customers["email_address"].duplicated(keep=False).sum()),
        "missing_customer_id": int(customers["customer_id"].str.strip().eq("").sum()),
        "missing_customer_name": int(customers["customer_name"].str.strip().eq("").sum()),
        "missing_email_address": int(customers["email_address"].str.strip().eq("").sum()),
        "invalid_email_format": int((~customers["email_address"].str.match(email_pattern, na=False) & customers["email_address"].str.strip().ne("")).sum()),
        "missing_phone_number": int(customers["phone_number"].str.strip().eq("").sum()),
        "invalid_customer_since_date": invalid_date_count(customers["customer_since"]),
    }


def validate_orders(orders, customer_ids):
    amounts = pd.to_numeric(orders["order_amount"], errors="coerce")
    return {
        "duplicate_order_id": int(orders["order_id"].duplicated(keep=False).sum()),
        "missing_customer_id": int(orders["customer_id"].str.strip().eq("").sum()),
        "missing_product_id": int(orders["product_id"].str.strip().eq("").sum()),
        "missing_product_name": int(orders["product_name"].str.strip().eq("").sum()),
        "missing_order_date": int(orders["order_date"].str.strip().eq("").sum()),
        "invalid_order_date": invalid_date_count(orders["order_date"]),
        "invalid_order_status": int((~orders["order_status"].isin(VALID_ORDER_STATUSES)).sum()),
        "invalid_payment_status": int((~orders["payment_status"].isin(VALID_PAYMENT_STATUSES)).sum()),
        "invalid_order_amount": int((amounts.isna() | amounts.lt(0)).sum()),
        "orphan_customer_references": int((~orders["customer_id"].isin(customer_ids)).sum()),
    }


def validate_products(products):
    prices = pd.to_numeric(products["price"], errors="coerce")
    stock = pd.to_numeric(products["stock_quantity"], errors="coerce")
    ratings = pd.to_numeric(products["product_rating"], errors="coerce")
    valid_warranty = products["warranty_period"].str.match(r"^(No warranty|\d+ (month|months|year|years))$", na=False)
    return {
        "duplicate_product_id": int(products["product_id"].duplicated(keep=False).sum()),
        "missing_product_id": int(products["product_id"].str.strip().eq("").sum()),
        "missing_product_name": int(products["product_name"].str.strip().eq("").sum()),
        "missing_description": int(products["description"].str.strip().eq("").sum()),
        "invalid_price": int((prices.isna() | prices.lt(0)).sum()),
        "invalid_stock_quantity": int((stock.isna() | stock.lt(0) | stock.mod(1).ne(0)).sum()),
        "invalid_warranty_period": int((~valid_warranty).sum()),
        "invalid_product_rating": int((ratings.isna() | ratings.lt(0) | ratings.gt(5)).sum()),
        "invalid_returnable": int((~products["returnable"].isin({"Yes", "No"})).sum()),
    }


def validate_emails(emails, customer_ids, order_ids):
    timestamps = pd.to_datetime(emails["timestamp"].where(emails["timestamp"].str.strip().ne("")), errors="coerce")
    has_order_id = emails["order_id"].str.strip().ne("")
    return {
        "duplicate_email_id": int(emails["email_id"].duplicated(keep=False).sum()),
        "duplicate_email_content": int(emails["email_body"].duplicated(keep=False).sum()),
        "missing_customer_id": int(emails["customer_id"].str.strip().eq("").sum()),
        "missing_subject": int(emails["subject"].str.strip().eq("").sum()),
        "missing_email_body": int(emails["email_body"].str.strip().eq("").sum()),
        "invalid_timestamp": int(timestamps.isna().sum() - emails["timestamp"].str.strip().eq("").sum()),
        "invalid_category": int((~emails["category"].isin(VALID_CATEGORIES)).sum()),
        "invalid_order_id": int((has_order_id & ~emails["order_id"].isin(order_ids)).sum()),
        "orphan_customer_references": int((~emails["customer_id"].isin(customer_ids)).sum()),
        "orphan_order_references": int((has_order_id & ~emails["order_id"].isin(order_ids)).sum()),
    }


def clean_email_text(text):
    """Remove layout noise while retaining punctuation, IDs, prices, and wording."""
    if not isinstance(text, str):
        return text
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def normalize_categories(emails):
    original = emails["category"].copy()
    normalized_keys = original.astype(str).str.strip().str.replace(r"\s+", " ", regex=True).str.casefold()
    emails["category"] = normalized_keys.map(CATEGORY_LOOKUP).fillna(original.astype(str).str.strip())
    return int((original != emails["category"]).sum()), sorted(set(emails.loc[~emails["category"].isin(VALID_CATEGORIES), "category"]))


def clean_products(products):
    """Normalize display formatting without removing descriptive catalog detail."""
    for column in ["product_name", "description", "category", "subcategory", "brand", "available_sizes", "available_colors", "warranty_period"]:
        products[column] = products[column].map(clean_email_text)
    prices = pd.to_numeric(products["price"], errors="coerce")
    products.loc[prices.notna(), "price"] = prices[prices.notna()].map(lambda value: f"{value:.2f}")
    stock = pd.to_numeric(products["stock_quantity"], errors="coerce")
    products.loc[stock.notna() & stock.ge(0) & stock.mod(1).eq(0), "stock_quantity"] = stock[stock.notna() & stock.ge(0) & stock.mod(1).eq(0)].astype(int).astype(str)
    ratings = pd.to_numeric(products["product_rating"], errors="coerce")
    products.loc[ratings.notna() & ratings.between(0, 5), "product_rating"] = ratings[ratings.notna() & ratings.between(0, 5)].map(lambda value: f"{value:.1f}")
    returnable = products["returnable"].str.casefold().map({"yes": "Yes", "no": "No"})
    products.loc[returnable.notna(), "returnable"] = returnable[returnable.notna()]


def handle_missing_values(customers, products, orders, emails):
    """Standardize empty optional order IDs; required gaps stay visible for review."""
    for frame in (customers, products, orders, emails):
        for column in frame.columns:
            frame[column] = frame[column].astype(str).str.strip()
    # An empty order ID is valid for enquiry and general-support emails.
    emails["order_id"] = emails["order_id"].replace({"nan": "", "None": ""})
    # Do not invent customer details, order details, subjects, or bodies.
    return {
        "customers_missing_required": blank_count(customers),
        "products_missing_required": blank_count(products, [
            "product_id", "product_name", "category", "subcategory", "brand",
            "description", "price", "available_colors", "stock_quantity",
            "warranty_period", "returnable", "product_rating",
        ]),
        "orders_missing_required": blank_count(orders),
        "emails_missing_required": blank_count(emails, ["email_id", "customer_id", "subject", "email_body", "timestamp", "category"]),
        "emails_missing_optional_order_id": int(emails["order_id"].eq("").sum()),
    }


def remove_duplicates(frame):
    """Remove only rows identical in every column, preserving possible valid repeats."""
    cleaned = frame.drop_duplicates().copy()
    return cleaned, len(frame) - len(cleaned)


def validate_relationships(customers, products, orders, emails):
    customer_ids = set(customers["customer_id"])
    order_ids = set(orders["order_id"])
    product_names = dict(zip(products["product_id"], products["product_name"]))
    orphan_orders = int((~orders["customer_id"].isin(customer_ids)).sum())
    has_order = emails["order_id"].ne("")
    orphan_emails = int((~emails["customer_id"].isin(customer_ids)).sum())
    orphan_email_orders = int((has_order & ~emails["order_id"].isin(order_ids)).sum())
    invalid_order_products = int((~orders["product_id"].isin(product_names)).sum())
    product_name_mismatches = int(orders.apply(lambda row: row["product_id"] in product_names and row["product_name"] != product_names[row["product_id"]], axis=1).sum())
    return {
        "valid_order_customer_links": len(orders) - orphan_orders,
        "valid_email_customer_links": len(emails) - orphan_emails,
        "valid_email_order_links": int(has_order.sum()) - orphan_email_orders,
        "orphan_orders": orphan_orders,
        "orphan_emails": orphan_emails,
        "orphan_email_orders": orphan_email_orders,
        "orders_with_valid_product_ids": len(orders) - invalid_order_products,
        "orders_with_invalid_product_ids": invalid_order_products,
        "orders_with_product_name_mismatch": product_name_mismatches,
    }


def generate_statistics(emails):
    lengths = emails["email_body"].str.len()
    return {
        "minimum_length": int(lengths.min()), "maximum_length": int(lengths.max()),
        "average_length": round(float(lengths.mean()), 2), "median_length": round(float(lengths.median()), 2),
        "very_short_emails_under_40_characters": int(lengths.lt(40).sum()),
        "very_long_emails_over_500_characters": int(lengths.gt(500).sum()),
        "emails_with_order_id": int(emails["order_id"].ne("").sum()),
        "emails_without_order_id": int(emails["order_id"].eq("").sum()),
        "category_distribution": Counter(emails["category"]),
    }


def generate_report(path, original_rows, final_frames, validations, removed, missing, relationships, statistics, normalized_count, unknown_categories):
    lines = ["DATA QUALITY REPORT", "=" * 60, "", "CLEANING DECISIONS", "- Exact duplicate rows were removed only; conflicting duplicate IDs remain for review.", "- Required missing values are preserved and reported instead of being invented or deleted.", "- Empty email order_id values are valid and preserved as blank optional fields.", "- Email text has whitespace/layout cleanup only; punctuation and meaningful words are retained.", "- Known category formatting variants are normalized; unknown categories are reported unchanged.", "", "CUSTOMERS", f"Original rows: {original_rows['customers']}", f"Final rows: {len(final_frames['customers'])}", f"Duplicates removed: {removed['customers']}", f"Missing values: {missing['customers_missing_required']}"]
    lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in validations["customers"].items())
    lines.extend(["", "PRODUCTS", f"Original rows: {original_rows['products']}", f"Final rows: {len(final_frames['products'])}", f"Total products: {len(final_frames['products'])}", f"Duplicates removed: {removed['products']}", f"Missing required values: {missing['products_missing_required']}", "Note: available_sizes is optional for products that do not have sizes."])
    lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in validations["products"].items())
    lines.extend(["", "ORDERS", f"Original rows: {original_rows['orders']}", f"Final rows: {len(final_frames['orders'])}", f"Duplicates removed: {removed['orders']}", f"Missing values: {missing['orders_missing_required']}"])
    lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in validations["orders"].items())
    lines.extend(["", "EMAILS", f"Original rows: {original_rows['emails']}", f"Final rows: {len(final_frames['emails'])}", f"Duplicates removed: {removed['emails']}", f"Missing required values: {missing['emails_missing_required']}", f"Missing optional order IDs: {missing['emails_missing_optional_order_id']}", f"Categories normalized: {normalized_count}", f"Unknown categories: {', '.join(unknown_categories) if unknown_categories else 'None'}"])
    lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in validations["emails"].items())
    lines.extend(["", "RELATIONSHIP VALIDATION"])
    lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in relationships.items())
    lines.extend(["", "EMAIL STATISTICS"])
    for key, value in statistics.items():
        value = dict(value) if key == "category_distribution" else value
        lines.append(f"{key.replace('_', ' ').title()}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_clean_data(processed_directory, customers, products, orders, emails):
    processed_directory.mkdir(parents=True, exist_ok=True)
    customers.to_csv(processed_directory / "customers_cleaned.csv", index=False)
    products.to_csv(processed_directory / "products_cleaned.csv", index=False)
    orders.to_csv(processed_directory / "orders_cleaned.csv", index=False)
    emails.to_csv(processed_directory / "emails_cleaned.csv", index=False)


def main():
    root = project_root()
    raw, processed = root / "data" / "raw", root / "data" / "processed"
    customers, products, orders, emails = load_data(raw)
    original_rows = {"customers": len(customers), "products": len(products), "orders": len(orders), "emails": len(emails)}

    missing = handle_missing_values(customers, products, orders, emails)
    clean_products(products)
    normalized_count, unknown_categories = normalize_categories(emails)
    customers, removed_customers = remove_duplicates(customers)
    products, removed_products = remove_duplicates(products)
    orders, removed_orders = remove_duplicates(orders)
    emails, removed_emails = remove_duplicates(emails)

    customer_ids, order_ids = set(customers["customer_id"]), set(orders["order_id"])
    validations = {"customers": validate_customers(customers), "products": validate_products(products), "orders": validate_orders(orders, customer_ids), "emails": validate_emails(emails, customer_ids, order_ids)}
    relationships = validate_relationships(customers, products, orders, emails)
    statistics = generate_statistics(emails)
    save_clean_data(processed, customers, products, orders, emails)
    generate_report(processed / "data_quality_report.txt", original_rows, {"customers": customers, "products": products, "orders": orders, "emails": emails}, validations, {"customers": removed_customers, "products": removed_products, "orders": removed_orders, "emails": removed_emails}, missing, relationships, statistics, normalized_count, unknown_categories)

    print("Preprocessing complete.")
    print(f"Customers: {len(customers)} | Products: {len(products)} | Orders: {len(orders)} | Emails: {len(emails)}")
    print(f"Duplicates removed - customers: {removed_customers}, products: {removed_products}, orders: {removed_orders}, emails: {removed_emails}")
    print(f"Orphan emails: {relationships['orphan_emails']} | Orphan orders: {relationships['orphan_orders']}")
    print(f"Report: {processed / 'data_quality_report.txt'}")


if __name__ == "__main__":
    main()

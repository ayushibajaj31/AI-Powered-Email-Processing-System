"""Load the existing cleaned CSV files into PostgreSQL after `alembic upgrade head`.

The source files are read only. The loader stops on invalid references instead of
inventing customers, products, or orders.
"""

from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.database import configure_database
from src.database.models import Customer, Email, Order, OrderItem, Product


DATA = ROOT / "data" / "processed"


def required(row, field, file_name):
    value = str(row.get(field, "")).strip()
    if not value or value.lower() == "nan":
        raise ValueError(f"{file_name}: required field '{field}' is missing.")
    return value


def optional(row, field):
    value = str(row.get(field, "")).strip()
    return None if not value or value.lower() == "nan" else value


def number(value, field, file_name, integer=False):
    try:
        return int(value) if integer else Decimal(str(value))
    except (ValueError, InvalidOperation) as error:
        raise ValueError(f"{file_name}: '{field}' must be numeric.") from error


def read_csv(name):
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(f"Required input file was not found: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def require_empty(session):
    for model in (Customer, Product, Order, Email):
        if session.scalar(select(model.id).limit(1)) is not None:
            raise ValueError("The database already contains application data. Refusing to create duplicate records.")


def load_data():
    engine = configure_database()
    customers_frame = read_csv("customers_cleaned.csv")
    products_frame = read_csv("products_cleaned.csv")
    orders_frame = read_csv("orders_cleaned.csv")
    emails_frame = read_csv("emails_cleaned.csv")

    from src.database.database import SessionLocal
    with SessionLocal() as session:
        try:
            require_empty(session)
            customers = {}
            for _, row in customers_frame.iterrows():
                business_id = required(row, "customer_id", "customers_cleaned.csv")
                if business_id in customers:
                    raise ValueError(f"customers_cleaned.csv: duplicate customer_id '{business_id}'.")
                since = datetime.combine(datetime.strptime(required(row, "customer_since", "customers_cleaned.csv"), "%Y-%m-%d").date(), time.min)
                customer = Customer(
                    customer_id=business_id,
                    name=required(row, "customer_name", "customers_cleaned.csv"),
                    email=required(row, "email_address", "customers_cleaned.csv"),
                    phone=optional(row, "phone_number"),
                    created_at=since,
                )
                session.add(customer)
                customers[business_id] = customer
            session.flush()

            products = {}
            for _, row in products_frame.iterrows():
                business_id = required(row, "product_id", "products_cleaned.csv")
                if business_id in products:
                    raise ValueError(f"products_cleaned.csv: duplicate product_id '{business_id}'.")
                product = Product(
                    product_id=business_id,
                    product_name=required(row, "product_name", "products_cleaned.csv"),
                    category=required(row, "category", "products_cleaned.csv"),
                    description=required(row, "description", "products_cleaned.csv"),
                    price=number(required(row, "price", "products_cleaned.csv"), "price", "products_cleaned.csv"),
                    stock=number(required(row, "stock_quantity", "products_cleaned.csv"), "stock_quantity", "products_cleaned.csv", integer=True),
                    warranty=optional(row, "warranty_period"),
                    available_sizes=optional(row, "available_sizes"),
                    available_colors=optional(row, "available_colors"),
                )
                session.add(product)
                products[business_id] = product
            session.flush()

            seen_orders = set()
            for _, row in orders_frame.iterrows():
                order_code = required(row, "order_id", "orders_cleaned.csv")
                if order_code in seen_orders:
                    raise ValueError(f"orders_cleaned.csv: duplicate order_id '{order_code}'.")
                seen_orders.add(order_code)
                customer_code = required(row, "customer_id", "orders_cleaned.csv")
                product_code = required(row, "product_id", "orders_cleaned.csv")
                if customer_code not in customers:
                    raise ValueError(f"orders_cleaned.csv: order '{order_code}' references missing customer '{customer_code}'.")
                if product_code not in products:
                    raise ValueError(f"orders_cleaned.csv: order '{order_code}' references missing product '{product_code}'.")
                amount = number(required(row, "order_amount", "orders_cleaned.csv"), "order_amount", "orders_cleaned.csv")
                product = products[product_code]
                quantity = int(amount / product.price) if product.price and amount / product.price == int(amount / product.price) else 1
                order = Order(
                    order_id=order_code, customer_id=customers[customer_code].id,
                    order_date=datetime.strptime(required(row, "order_date", "orders_cleaned.csv"), "%Y-%m-%d").date(),
                    status=required(row, "order_status", "orders_cleaned.csv"),
                    payment_status=required(row, "payment_status", "orders_cleaned.csv"), total_amount=amount,
                )
                session.add(order)
                session.flush()
                session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=max(quantity, 1), unit_price=product.price))

            seen_emails = set()
            for _, row in emails_frame.iterrows():
                email_code = required(row, "email_id", "emails_cleaned.csv")
                if email_code in seen_emails:
                    raise ValueError(f"emails_cleaned.csv: duplicate email_id '{email_code}'.")
                seen_emails.add(email_code)
                customer_code = required(row, "customer_id", "emails_cleaned.csv")
                if customer_code not in customers:
                    raise ValueError(f"emails_cleaned.csv: email '{email_code}' references missing customer '{customer_code}'.")
                session.add(Email(
                    email_id=email_code, customer_id=customers[customer_code].id,
                    subject=required(row, "subject", "emails_cleaned.csv"), body=required(row, "email_body", "emails_cleaned.csv"),
                    predicted_category=optional(row, "category"),
                    created_at=datetime.fromisoformat(required(row, "timestamp", "emails_cleaned.csv")),
                ))
            session.commit()
        except Exception:
            session.rollback()
            raise

    print(f"Loaded {len(customers)} customers, {len(products)} products, {len(seen_orders)} orders, and {len(seen_emails)} emails.")
    engine.dispose()


if __name__ == "__main__":
    try:
        load_data()
    except Exception as error:
        print(f"Data loading failed: {error}")
        raise SystemExit(1)

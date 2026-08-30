"""Create a local development user linked to an existing PostgreSQL customer."""

import argparse
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.auth.security import hash_password
from src.database.database import configure_database
from src.database.models import Customer, User


def main():
    parser = argparse.ArgumentParser(description="Create a development JWT test user.")
    parser.add_argument("--email", default="customer101@example.com")
    parser.add_argument("--password", default="TestPassword123!", help="Development-only password; it is stored only as an Argon2 hash.")
    parser.add_argument("--customer-id", default="CUST0001", help="Existing customer ID to link to this user.")
    args = parser.parse_args()

    configure_database()
    from src.database.database import SessionLocal
    with SessionLocal() as session:
        customer = session.scalar(select(Customer).where(Customer.customer_id == args.customer_id))
        if customer is None:
            print(f"Test user was not created: customer '{args.customer_id}' does not exist.")
            raise SystemExit(1)
        if session.scalar(select(User).where(User.email == args.email.lower())):
            print("Test user already exists; no password was changed.")
            return
        if session.scalar(select(User).where(User.customer_id == customer.id)):
            print(f"Test user was not created: customer '{args.customer_id}' already has a user account.")
            raise SystemExit(1)
        session.add(User(
            customer_id=customer.id,
            email=args.email.lower(),
            password_hash=hash_password(args.password),
            role="customer",
            is_active=True,
        ))
        session.commit()
    print(f"Test user created for customer '{args.customer_id}'.")


if __name__ == "__main__":
    main()

"""Check that DATABASE_URL can connect to PostgreSQL."""

import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.database import configure_database


def main():
    try:
        engine = configure_database()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection successful.")
    except Exception as error:
        print(f"Database connection failed: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

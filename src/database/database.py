"""SQLAlchemy engine and session management; schema creation is handled by Alembic."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


load_dotenv()


class Base(DeclarativeBase):
    pass


def database_url():
    url = os.getenv("DATABASE_URL")
    if not url or "username:password" in url:
        raise RuntimeError("DATABASE_URL is not configured. Set a valid PostgreSQL URL in .env.")
    return url


def build_engine(url=None):
    resolved_url = url or database_url()
    # This branch is only for fast, isolated unit tests. Production uses PostgreSQL.
    if resolved_url.startswith("sqlite"):
        return create_engine(
            resolved_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(resolved_url, pool_pre_ping=True)


engine = None
SessionLocal = None


def configure_database(url=None):
    """Configure an engine lazily; tests can provide an isolated SQLite URL."""
    global engine, SessionLocal
    engine = build_engine(url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return engine


def get_session():
    if SessionLocal is None:
        configure_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

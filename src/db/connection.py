"""Database connection helpers."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DEFAULT_DATABASE_URL = "sqlite:///./worldcup2026.db"


def get_database_url() -> str:
    """Return the configured database URL."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the configured database."""
    url = database_url or get_database_url()
    return create_engine(url, future=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, future=True)


def get_session(database_url: str | None = None) -> Session:
    """Return a new SQLAlchemy session."""
    engine = get_engine(database_url)
    SessionLocal.configure(bind=engine)
    return SessionLocal()

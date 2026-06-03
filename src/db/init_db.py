"""Create all database tables."""

from __future__ import annotations

from src.db import models  # noqa: F401
from src.db.base import Base
from src.db.connection import get_database_url, get_engine


def main() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized successfully using {get_database_url()}")


if __name__ == "__main__":
    main()

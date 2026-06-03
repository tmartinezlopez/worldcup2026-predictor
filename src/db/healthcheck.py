"""Database connectivity healthcheck."""

from __future__ import annotations

from sqlalchemy import text

from src.db.connection import get_database_url, get_session


def main() -> None:
    with get_session() as session:
        result = session.execute(text("SELECT 1")).scalar_one()
    print(f"Database healthcheck passed for {get_database_url()}: SELECT {result}")


if __name__ == "__main__":
    main()

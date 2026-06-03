"""Drop all database tables in development."""

from __future__ import annotations

import argparse
import sys

from src.db import models  # noqa: F401
from src.db.base import Base
from src.db.connection import get_database_url, get_engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Drop all database tables.")
    parser.add_argument(
        "--yes-i-know",
        action="store_true",
        help="Acknowledge that this destructive action is intended.",
    )
    args = parser.parse_args()

    if not args.yes_i_know:
        print("Refusing to drop tables without --yes-i-know", file=sys.stderr)
        raise SystemExit(1)

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    print(f"Database tables dropped successfully using {get_database_url()}")


if __name__ == "__main__":
    main()

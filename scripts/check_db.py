"""Verify MySQL connectivity and list sample patents."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from src.db import get_session


def main() -> int:
    try:
        with get_session() as session:
            rows = session.execute(
                text("SELECT patent_id, title FROM patents LIMIT 10")
            ).all()
    except Exception as exc:
        print(f"Database connection failed: {exc}")
        return 1

    if not rows:
        print("Connected, but patents table is empty.")
        return 0

    print("Connected. Sample patents:")
    for patent_id, title in rows:
        print(f"  - {patent_id}: {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

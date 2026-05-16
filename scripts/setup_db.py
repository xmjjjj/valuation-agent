"""
Initialize database without mysql CLI (pure Python).
Usage:
  python scripts/setup_db.py
  python scripts/setup_db.py --root-password YOUR_ROOT_PASSWORD
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
INIT_DIR = ROOT / "db" / "init"

DB_NAME = "patent_valuation"
APP_USER = "patent"
APP_PASSWORD = "patent_dev"


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _split_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buffer).strip()
            if stmt:
                statements.append(stmt)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def _exec_script(cursor, path: Path) -> None:
    sql = _read_sql(path)
    for stmt in _split_statements(sql):
        cursor.execute(stmt)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize patent_valuation MySQL database")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--root-user", default="root")
    parser.add_argument("--root-password", default="")
    args = parser.parse_args()

    root_password = args.root_password or getpass.getpass(
        f"MySQL root password for {args.root_user}@localhost: "
    )

    try:
        conn = pymysql.connect(
            host=args.host,
            port=args.port,
            user=args.root_user,
            password=root_password,
            charset="utf8mb4",
            autocommit=True,
        )
    except pymysql.Error as exc:
        print(f"Cannot connect as root: {exc}")
        return 1

    print("Connected to MySQL.")

    with conn.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        print(f"Database `{DB_NAME}` ready.")

        for ddl in (
            f"CREATE USER IF NOT EXISTS '{APP_USER}'@'localhost' IDENTIFIED BY '{APP_PASSWORD}'",
            f"CREATE USER IF NOT EXISTS '{APP_USER}'@'%' IDENTIFIED BY '{APP_PASSWORD}'",
            f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{APP_USER}'@'localhost'",
            f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{APP_USER}'@'%'",
            "FLUSH PRIVILEGES",
        ):
            cursor.execute(ddl)
        print(f"User `{APP_USER}` ready.")

    conn.select_db(DB_NAME)
    conn.autocommit(False)

    for name in ("01_schema.sql", "02_seed.sql"):
        path = INIT_DIR / name
        print(f"Running {name} ...")
        with conn.cursor() as cursor:
            try:
                _exec_script(cursor, path)
                conn.commit()
            except pymysql.Error as exc:
                conn.rollback()
                print(f"Failed on {name}: {exc}")
                return 1

    conn.close()
    print("Schema and seed data loaded successfully.")
    print(f"\nUse in .env: MYSQL_USER={APP_USER} MYSQL_PASSWORD={APP_PASSWORD} MYSQL_DATABASE={DB_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

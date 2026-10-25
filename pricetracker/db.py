import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "price_tracker.db"


def _connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            currency TEXT,
            target_price TEXT
        );
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            price TEXT NOT NULL CHECK (CAST(price AS REAL) >= 0),
            currency TEXT,
            recorded_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_price_history_product_time
            ON price_history(product_id, recorded_at);
        """
    )
    product_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(products)")
    }
    if "target_price" not in product_columns:
        connection.execute("ALTER TABLE products ADD COLUMN target_price TEXT")
    return connection


def _as_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def add_product(
    name: str,
    url: str,
    currency: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    target_price: Decimal | int | float | str | None = None,
) -> int:
    """Add a product and return its database ID."""
    target = Decimal(str(target_price)) if target_price is not None else None
    if target is not None and (not target.is_finite() or target < 0):
        raise ValueError("Harga sasaran mesti nombor sah dan tidak negatif.")
    target_value = str(target) if target is not None else None
    with closing(_connect(db_path)) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO products (name, url, currency, target_price) "
            "VALUES (?, ?, ?, ?)",
            (name, url, currency.upper() if currency else None, target_value),
        )
        return int(cursor.lastrowid)


def list_products(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return all tracked products ordered by database ID."""
    with closing(_connect(db_path)) as connection, connection:
        rows = connection.execute(
            "SELECT id, name, url, currency, target_price FROM products ORDER BY id"
        ).fetchall()
        return [_as_dict(row) for row in rows]


def remove_product(product_id: int, db_path: str | Path = DEFAULT_DB_PATH) -> bool:
    """Remove a product and its history; return whether it existed."""
    with closing(_connect(db_path)) as connection, connection:
        cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return cursor.rowcount > 0


def record_price(
    product_id: int,
    price: Decimal | int | float | str,
    currency: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    recorded_at: str | None = None,
) -> int:
    """Record a product price and return the new history row ID."""
    price_value = Decimal(str(price))
    if not price_value.is_finite() or price_value < 0:
        raise ValueError("Harga mesti nombor perpuluhan yang sah dan tidak negatif.")

    currency_value = currency.upper() if currency else None
    timestamp = recorded_at or datetime.now(timezone.utc).isoformat()
    with closing(_connect(db_path)) as connection, connection:
        cursor = connection.execute(
            """
            INSERT INTO price_history (product_id, price, currency, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (product_id, str(price_value), currency_value, timestamp),
        )
        if currency_value:
            connection.execute(
                "UPDATE products SET currency = ? WHERE id = ?",
                (currency_value, product_id),
            )
        return int(cursor.lastrowid)


def get_history(
    product_id: int,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return a product's price history from oldest to newest."""
    with closing(_connect(db_path)) as connection, connection:
        rows = connection.execute(
            """
            SELECT id, product_id, price, currency, recorded_at
            FROM price_history
            WHERE product_id = ?
            ORDER BY recorded_at, id
            """,
            (product_id,),
        ).fetchall()
        return [_as_dict(row) for row in rows]

import argparse
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence
from urllib.error import URLError

from pricetracker.db import (
    DEFAULT_DB_PATH,
    add_product,
    get_history,
    list_products,
    record_price,
    remove_product,
)
from pricetracker.prices import PriceNotFoundError, fetch_product


def _target_price(value: str) -> Decimal:
    try:
        price = Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError("harga sasaran mesti nombor") from error
    if not price.is_finite() or price < 0:
        raise argparse.ArgumentTypeError("harga sasaran mesti sah dan tidak negatif")
    return price


def _price_label(price: str | Decimal, currency: str | None) -> str:
    return f"{currency} {price}" if currency else str(price)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="price-tracker")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Laluan fail SQLite (lalai: price_tracker.db dalam projek)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add_command = commands.add_parser("add", help="Tambah produk untuk dijejak")
    add_command.add_argument("url", help="URL produk")
    add_command.add_argument("--target", type=_target_price, help="Harga sasaran")

    commands.add_parser("list", help="Senaraikan produk dijejak")
    commands.add_parser("check", help="Semak dan simpan harga terkini")

    history_command = commands.add_parser("history", help="Lihat sejarah harga")
    history_command.add_argument("id", type=int, help="ID produk")

    remove_command = commands.add_parser("remove", help="Buang produk")
    remove_command.add_argument("id", type=int, help="ID produk")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    db_path = args.db_path or DEFAULT_DB_PATH

    if args.command == "add":
        product = fetch_product(args.url)
        product_id = add_product(
            product.name,
            args.url,
            currency=product.currency,
            db_path=db_path,
            target_price=args.target,
        )
        record_price(
            product_id,
            product.price,
            currency=product.currency,
            db_path=db_path,
        )
        print(
            f"Ditambah [{product_id}] {product.name}: "
            f"{_price_label(product.price, product.currency)}"
        )
        if args.target is not None:
            print(f"Harga sasaran: {_price_label(args.target, product.currency)}")
        return 0

    selected_db = db_path
    if args.command == "list":
        products = list_products(selected_db)
        if not products:
            print("Tiada produk dijejak.")
        for product in products:
            target = (
                f" (sasaran: {_price_label(product['target_price'], product['currency'])})"
                if product["target_price"] is not None
                else ""
            )
            print(
                f"[{product['id']}] {product['name']} — {product['url']} "
                f"— {product['currency'] or 'mata wang tidak diketahui'}{target}"
            )
        return 0

    if args.command == "check":
        return _check_products(selected_db)

    if args.command == "history":
        history = get_history(args.id, selected_db)
        if not history:
            print(f"Tiada sejarah harga untuk produk [{args.id}].")
            return 1
        for entry in history:
            print(
                f"{entry['recorded_at']} — "
                f"{_price_label(entry['price'], entry['currency'])}"
            )
        return 0

    if args.command == "remove":
        if remove_product(args.id, selected_db):
            print(f"Produk [{args.id}] dibuang.")
            return 0
        print(f"Produk [{args.id}] tidak ditemui.")
        return 1

    parser.error("Arahan tidak dikenali.")
    return 2


def _check_products(db_path: Path) -> int:
    had_errors = False
    products = list_products(db_path)
    if not products:
        print("Tiada produk dijejak.")
        return 0
    for product in products:
        try:
            current = fetch_product(product["url"])
            history = get_history(product["id"], db_path)
            previous = Decimal(history[-1]["price"]) if history else None
            record_price(
                product["id"],
                current.price,
                currency=current.currency,
                db_path=db_path,
            )
        except (OSError, URLError, PriceNotFoundError, ValueError, sqlite3.Error) as error:
            print(f"Ralat semak [{product['id']}] {product['name']}: {error}")
            had_errors = True
            continue

        print(
            f"[{product['id']}] {current.name}: "
            f"{_price_label(current.price, current.currency or product['currency'])}"
        )
        if previous is not None and current.price < previous:
            print(
                f"  Harga turun daripada "
                f"{_price_label(previous, product['currency'])}."
            )
        if product["target_price"] is not None:
            target = Decimal(product["target_price"])
            if current.price <= target:
                print(
                    f"  Harga mencapai sasaran "
                    f"{_price_label(target, current.currency or product['currency'])}."
                )
    return 1 if had_errors else 0

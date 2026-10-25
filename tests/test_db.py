from decimal import Decimal

import pytest

from pricetracker.db import (
    DEFAULT_DB_PATH,
    add_product,
    get_history,
    list_products,
    record_price,
    remove_product,
)


def test_default_database_is_in_data_directory():
    assert DEFAULT_DB_PATH.name == "price_tracker.db"
    assert DEFAULT_DB_PATH.parent.name == "data"


def test_add_product_creates_database_parent_directory(tmp_path):
    db_path = tmp_path / "nested" / "price_tracker.db"

    add_product("Kasut hiking", "https://example.com/shoe", db_path=db_path)

    assert db_path.is_file()


def test_add_and_list_products_with_currency(tmp_path):
    db_path = tmp_path / "products.db"

    product_id = add_product(
        "Kasut hiking", "https://example.com/shoe", currency="myr", db_path=db_path
    )

    assert list_products(db_path) == [
        {
            "id": product_id,
            "name": "Kasut hiking",
            "url": "https://example.com/shoe",
            "currency": "MYR",
            "target_price": None,
        }
    ]


def test_add_product_removes_tracking_query_parameters(tmp_path):
    db_path = tmp_path / "clean-url.db"
    tracked_url = (
        "https://example.com/shoe?color=blue&utm_source=mail"
        "&gclid=click-id&gad_campaignid=campaign&fbclid=social-id&page=2"
    )

    add_product("Kasut hiking", tracked_url, db_path=db_path)

    assert list_products(db_path)[0]["url"] == (
        "https://example.com/shoe?color=blue&page=2"
    )


def test_record_price_and_get_history_in_order(tmp_path):
    db_path = tmp_path / "history.db"
    product_id = add_product("Kasut hiking", "https://example.com/shoe", db_path=db_path)

    record_price(
        product_id,
        Decimal("258.99"),
        currency="myr",
        db_path=db_path,
        recorded_at="2026-10-25T09:00:00+00:00",
    )
    record_price(
        product_id,
        Decimal("249.50"),
        db_path=db_path,
        recorded_at="2026-10-26T09:00:00+00:00",
    )

    assert get_history(product_id, db_path) == [
        {
            "id": 1,
            "product_id": product_id,
            "price": "258.99",
            "currency": "MYR",
            "recorded_at": "2026-10-25T09:00:00+00:00",
        },
        {
            "id": 2,
            "product_id": product_id,
            "price": "249.50",
            "currency": None,
            "recorded_at": "2026-10-26T09:00:00+00:00",
        },
    ]
    assert list_products(db_path)[0]["currency"] == "MYR"


def test_remove_product_also_removes_history(tmp_path):
    db_path = tmp_path / "remove.db"
    product_id = add_product("Kasut hiking", "https://example.com/shoe", db_path=db_path)
    record_price(product_id, "258.99", db_path=db_path)

    assert remove_product(product_id, db_path)
    assert not remove_product(product_id, db_path)
    assert list_products(db_path) == []
    assert get_history(product_id, db_path) == []


def test_record_price_rejects_negative_value(tmp_path):
    db_path = tmp_path / "invalid.db"
    product_id = add_product("Kasut hiking", "https://example.com/shoe", db_path=db_path)

    with pytest.raises(ValueError):
        record_price(product_id, -1, db_path=db_path)

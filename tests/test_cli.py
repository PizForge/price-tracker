from decimal import Decimal

from pricetracker import cli
from pricetracker.db import add_product, get_history, list_products, record_price
from pricetracker.prices import ProductInfo


def test_add_fetches_product_and_records_initial_price(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "cli.db"
    tracked_url = "https://example.com/shoe?utm_source=mail&color=blue&fbclid=social-id"
    monkeypatch.setattr(
        cli,
        "fetch_product",
        lambda url: ProductInfo("Kasut hiking", Decimal("258.99"), "MYR"),
    )

    result = cli.main(
        ["--db-path", str(db_path), "add", tracked_url, "--target", "250"]
    )

    assert result == 0
    assert "[1] Kasut hiking" in capsys.readouterr().out
    product = list_products(db_path)[0]
    assert product["url"] == "https://example.com/shoe?color=blue"
    assert product["target_price"] == "250"
    assert product["currency"] == "MYR"
    assert get_history(product["id"], db_path)[0]["price"] == "258.99"


def test_list_history_and_remove_commands(tmp_path, capsys):
    db_path = tmp_path / "cli.db"
    product_id = add_product(
        "Kasut hiking",
        "https://example.com/shoe",
        currency="MYR",
        db_path=db_path,
        target_price="250",
    )
    record_price(
        product_id,
        "258.99",
        currency="MYR",
        db_path=db_path,
        recorded_at="2026-10-25T09:00:00+00:00",
    )

    assert cli.main(["--db-path", str(db_path), "list"]) == 0
    assert "Kasut hiking" in capsys.readouterr().out

    assert cli.main(["--db-path", str(db_path), "history", str(product_id)]) == 0
    assert "258.99" in capsys.readouterr().out

    assert cli.main(["--db-path", str(db_path), "remove", str(product_id)]) == 0
    assert list_products(db_path) == []


def test_check_saves_price_and_reports_drop_and_target(
    tmp_path, monkeypatch, capsys
):
    db_path = tmp_path / "cli.db"
    product_id = add_product(
        "Kasut hiking",
        "https://example.com/shoe",
        currency="MYR",
        db_path=db_path,
        target_price="250",
    )
    record_price(product_id, "280.00", currency="MYR", db_path=db_path)
    monkeypatch.setattr(
        cli,
        "fetch_product",
        lambda url: ProductInfo("Kasut hiking", Decimal("249.50"), "MYR"),
    )

    result = cli.main(["--db-path", str(db_path), "check"])

    output = capsys.readouterr().out
    assert result == 0
    assert "Harga turun" in output
    assert "mencapai sasaran" in output
    assert get_history(product_id, db_path)[-1]["price"] == "249.50"


def test_check_reports_fetch_error_and_continues(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "cli.db"
    add_product("Produk", "https://example.com/item", db_path=db_path)

    def fail_fetch(url):
        raise OSError("sambungan gagal")

    monkeypatch.setattr(cli, "fetch_product", fail_fetch)

    assert cli.main(["--db-path", str(db_path), "check"]) == 1
    assert "sambungan gagal" in capsys.readouterr().out

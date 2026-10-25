import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from pricetracker.prices import (
    PriceNotFoundError,
    _to_decimal,
    fetch_price,
    fetch_product,
)


def _mock_response(html: str) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = html.encode()
    return response


class FetchPriceTests(unittest.TestCase):
    @patch("pricetracker.prices.urlopen")
    def test_fetches_price_from_json_ld(self, urlopen):
        urlopen.return_value = _mock_response(
            '<script type="application/ld+json">'
            '{"@type":"Product","offers":{"@type":"Offer","price":"12.50"}}'
            "</script>"
        )

        self.assertEqual(str(fetch_price("https://example.com/item")), "12.50")

    @patch("pricetracker.prices.urlopen")
    def test_fetches_price_from_product_meta(self, urlopen):
        urlopen.return_value = _mock_response(
            '<meta itemprop="price" content="RM 1,299.90">'
        )

        self.assertEqual(str(fetch_price("https://example.com/item")), "1299.90")

    def test_rejects_non_http_urls(self):
        with self.assertRaises(ValueError):
            fetch_price("file:///etc/passwd")

    @patch("pricetracker.prices.urlopen")
    def test_raises_when_page_has_no_price(self, urlopen):
        urlopen.return_value = _mock_response("<html><body>Tiada harga</body></html>")

        with self.assertRaises(PriceNotFoundError):
            fetch_price("https://example.com/item")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("RM1, 399.00", "1399.00"),
        ("RM 1,399.00", "1399.00"),
    ],
)
def test_parses_malaysian_ringgit_price(text, expected):
    assert _to_decimal(text) == Decimal(expected)


def test_fetch_product_prefers_json_ld_over_meta(monkeypatch):
    monkeypatch.setattr(
        "pricetracker.prices.urlopen",
        MagicMock(return_value=_mock_response(
            '<meta property="og:title" content="Meta Product">'
            '<meta property="product:price:amount" content="RM99.00">'
            '<script type="application/ld+json">'
            '{"@type":"Product","name":"JSON-LD Product",'
            '"offers":{"@type":"Offer","price":"RM1, 399.00",'
            '"priceCurrency":"MYR"}}'
            "</script>"
        )),
    )

    product = fetch_product("https://example.com/item")

    assert product.name == "JSON-LD Product"
    assert product.price == Decimal("1399.00")
    assert product.currency == "MYR"


def test_fetch_product_uses_meta_when_json_ld_is_missing(monkeypatch):
    monkeypatch.setattr(
        "pricetracker.prices.urlopen",
        MagicMock(return_value=_mock_response(
            '<meta property="og:title" content="Meta Product">'
            '<meta property="product:price:amount" content="RM1, 399.00">'
        )),
    )

    product = fetch_product("https://example.com/item")

    assert product.name == "Meta Product"
    assert product.price == Decimal("1399.00")


if __name__ == "__main__":
    unittest.main()

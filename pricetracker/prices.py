import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class PriceNotFoundError(ValueError):
    """Raised when a page does not expose a recognizable product name and price."""


@dataclass(frozen=True)
class ProductInfo:
    name: str
    price: Decimal


class _PriceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_names: list[str] = []
        self.meta_prices: list[str] = []
        self.json_ld: list[str] = []
        self._inside_json_ld = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}

        if tag.lower() == "meta":
            itemprop = attributes.get("itemprop", "").lower()
            property_name = attributes.get("property", "").lower()
            name = attributes.get("name", "").lower()
            content = attributes.get("content", "")

            if itemprop == "name" or property_name in {
                "og:title",
                "product:name",
            } or name in {"og:title", "twitter:title"}:
                if content:
                    self.meta_names.append(content.strip())

            if (
                "price" in itemprop
                or property_name in {"product:price:amount", "og:price:amount"}
                or name in {"product:price:amount", "og:price:amount"}
            ):
                if content:
                    self.meta_prices.append(content)

        if tag.lower() == "script":
            self._inside_json_ld = "ld+json" in attributes.get("type", "").lower()
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._inside_json_ld:
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._inside_json_ld:
            self.json_ld.append("".join(self._script_parts))
            self._inside_json_ld = False
            self._script_parts = []


def _product_values(value: object):
    if isinstance(value, dict):
        product_type = value.get("@type", [])
        if isinstance(product_type, str):
            product_type = [product_type]
        if isinstance(product_type, list) and any(
            item.lower() == "product" for item in product_type if isinstance(item, str)
        ):
            name = value.get("name")
            offers = value.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            prices = []
            if isinstance(offers, list):
                for offer in offers:
                    if isinstance(offer, dict):
                        prices.extend(
                            offer.get(key)
                            for key in ("price", "lowPrice", "highPrice")
                            if offer.get(key) is not None
                        )
            yield name, prices
        for item in value.values():
            yield from _product_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _product_values(item)


def _to_decimal(value: object) -> Decimal | None:
    if isinstance(value, (int, float, Decimal)):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None

    text = re.sub(r"[^\d.,+-]", "", text)
    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text:
        trailing_digits = len(text.rsplit(",", 1)[-1])
        text = text.replace(",", "." if trailing_digits in {1, 2} else "")

    try:
        price = Decimal(text)
    except InvalidOperation:
        return None
    return price if price.is_finite() and price >= 0 else None


def _fetch_product_data(url: str, timeout: float) -> tuple[str, Decimal | None]:
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("URL mesti menggunakan HTTP atau HTTPS.")

    request = Request(url, headers={"User-Agent": "PriceTracker/0.1"})
    with urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = _PriceParser()
    parser.feed(html)

    name = ""
    price: Decimal | None = None
    for script in parser.json_ld:
        try:
            structured_data = json.loads(script)
        except json.JSONDecodeError:
            continue
        for product_name, product_prices in _product_values(structured_data):
            if isinstance(product_name, str) and product_name.strip() and not name:
                name = product_name.strip()
            for candidate in product_prices:
                price = _to_decimal(candidate)
                if price is not None:
                    break
            if price is not None:
                break

    if not name:
        name = next((item for item in parser.meta_names if item), "")
    if price is None:
        for candidate in parser.meta_prices:
            price = _to_decimal(candidate)
            if price is not None:
                break

    return name, price


def fetch_product(url: str, timeout: float = 10.0) -> ProductInfo:
    """Fetch a product name and price, preferring JSON-LD over meta tags."""
    name, price = _fetch_product_data(url, timeout)
    if name and price is not None:
        return ProductInfo(name=name, price=price)

    raise PriceNotFoundError("Nama atau harga produk tidak ditemui dalam halaman.")


def fetch_price(url: str, timeout: float = 10.0) -> Decimal:
    """Fetch a product page and return its machine-readable price."""
    _, price = _fetch_product_data(url, timeout)
    if price is not None:
        return price
    raise PriceNotFoundError("Harga produk tidak ditemui dalam metadata halaman.")

# Price Tracker

Python project for retrieving product names and prices from product pages.

## Project structure

```text
Price-Tracker/
├── pricetracker/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── db.py
│   └── prices.py
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_db.py
│   └── test_prices.py
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## Getting started

Create and activate a virtual environment, then install the project:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

`pricetracker.prices.fetch_product(url)` fetches an HTTP(S) product page and
returns `ProductInfo` with the product name and price. It checks JSON-LD first,
then falls back to product meta tags. `fetch_price(url)` remains available to
return only the `Decimal` price. Missing product data raises
`PriceNotFoundError`.

`pricetracker.db` provides `add_product`, `list_products`, `remove_product`,
`record_price`, and `get_history` backed by SQLite. Database functions accept
an optional `db_path`; product currency is taken from JSON-LD `priceCurrency`
when available and stored alongside product and price history records.

Use the command-line interface with `python -m pricetracker`:

```powershell
python -m pricetracker add "https://example.com/product" --target 250.00
python -m pricetracker list
python -m pricetracker check
python -m pricetracker history 1
python -m pricetracker remove 1
```

The optional global `--db-path` argument selects a SQLite database file.
`check` stores each successful fetch and reports price drops or prices at or
below the configured target. Adding a product stores its first observed price
as the starting point for later comparisons.

Install test dependencies and run the pytest suite with:

```powershell
python -m pip install -e ".[test]"
python -m pytest
```

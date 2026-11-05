"""Catalog loaded from data/club-catalog.csv.

The engine reads this module. Re-seed after replacing the CSV.
"""

from __future__ import annotations

from app.catalog.load import build_catalog

_CATALOG = build_catalog()
BRANDS = _CATALOG["brands"]
HEADS = _CATALOG["heads"]
SHAFTS = _CATALOG["shafts"]


def get_catalog() -> dict:
    return {"brands": BRANDS, "heads": HEADS, "shafts": SHAFTS}

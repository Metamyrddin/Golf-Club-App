"""US customary units at the edges. The fitting chart stays metric.

Body inputs are feet, inches, and pounds. This module converts them to
centimetres and kilograms before a rule runs, and back again before a
sheet is shown. Shaft weights stay in grams — that is how the catalog
is specified, not a body measurement.
"""

from __future__ import annotations

CM_PER_INCH = 2.54
LB_PER_KG = 2.2046226218


def inches_to_cm(inches: float) -> float:
    return float(inches) * CM_PER_INCH


def cm_to_inches(cm: float, places: int = 1) -> float:
    return round(float(cm) / CM_PER_INCH, places)


def ft_in_to_cm(feet: float, inches: float = 0) -> float:
    return inches_to_cm(float(feet) * 12 + float(inches or 0))


def cm_to_ft_in(cm: float) -> tuple[int, float]:
    total = float(cm) / CM_PER_INCH
    feet = int(total // 12)
    inches = round(total - feet * 12, 1)
    if inches >= 12:
        feet += 1
        inches = 0.0
    return feet, inches


def format_height(cm: float) -> str:
    feet, inches = cm_to_ft_in(cm)
    inch_text = f"{inches:.0f}" if inches == int(inches) else f"{inches:.1f}"
    return f"{feet}'{inch_text}\""


def lb_to_kg(pounds: float) -> float:
    return float(pounds) / LB_PER_KG


def kg_to_lb(kg: float) -> float:
    return round(float(kg) * LB_PER_KG, 1)

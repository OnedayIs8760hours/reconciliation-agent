"""值归一化工具。"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"\s+", "", text)
    return text or None


def normalize_spec(value: Any) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    return text.replace("*", "x").replace("×", "x").lower()


def to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        text = str(value).replace(",", "").strip()
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1]
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def to_float(value: Any) -> float:
    return float(to_decimal(value))


def normalize_date_key(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return text[:10] if text else None


def month_key(value: Any) -> str | None:
    date_key = normalize_date_key(value)
    return date_key[:7] if date_key and len(date_key) >= 7 else None

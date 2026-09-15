from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

CATEGORIES = frozenset({"finance", "auto_service", "contract", "health", "note", "other"})


def parse_date(value: Any, *, formats: tuple[str, ...] = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y")) -> date | None:
    """Parse a date from common string formats."""
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(value: Any) -> Decimal | None:
    """Parse a monetary amount into Decimal."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", ".").replace(" ", ""))
    except (InvalidOperation, ValueError):
        return None


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a model response."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def normalize_category(value: Any, *, default: str = "other") -> str:
    category = str(value or default).strip()
    return category if category in CATEGORIES else default


def normalize_optional_category(value: Any) -> str | None:
    if value is None or value == "" or value == "null":
        return None
    category = str(value).strip()
    return category if category in CATEGORIES else None

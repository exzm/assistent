from datetime import date
from decimal import Decimal

import pytest

from app.utils.parsing import (
    extract_json_object,
    normalize_category,
    normalize_optional_category,
    parse_amount,
    parse_date,
)
from app.utils.text import clip_telegram, escape_html, join_nonempty, markdown_lite_to_html, prepare_telegram_html
from app.utils.vectors import normalize_vector, vector_literal


def test_parse_date_formats():
    assert parse_date("2024-01-02") == date(2024, 1, 2)
    assert parse_date("02.01.2024") == date(2024, 1, 2)
    assert parse_date("02/01/2024") == date(2024, 1, 2)
    assert parse_date("nope") is None
    assert parse_date(None) is None
    assert parse_date(123) is None


def test_parse_amount():
    assert parse_amount("1 234,56") == Decimal("1234.56")
    assert parse_amount(10) == Decimal("10")
    assert parse_amount(None) is None
    assert parse_amount("") is None
    assert parse_amount("bad") is None


def test_extract_json_object_variants():
    assert extract_json_object('{"a": 1}') == {"a": 1}
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json_object('prefix {"a": 1} suffix') == {"a": 1}
    assert extract_json_object("[1,2]") == {}
    assert extract_json_object("no json") == {}
    assert extract_json_object("{not-json") == {}
    assert extract_json_object('{"ok": true} trailing') == {"ok": True}


def test_categories():
    assert normalize_category("finance") == "finance"
    assert normalize_category("weird") == "other"
    assert normalize_optional_category("null") is None
    assert normalize_optional_category("") is None
    assert normalize_optional_category("health") == "health"
    assert normalize_optional_category("weird") is None


def test_text_helpers():
    assert clip_telegram("hi") == "hi"
    assert clip_telegram("x" * 10, limit=5).endswith("…(truncated)")
    assert join_nonempty("a", None, "b") == "a\nb"
    assert escape_html("a<b>") == "a&lt;b&gt;"
    assert markdown_lite_to_html("say **hi** now") == "say <b>hi</b> now"
    assert markdown_lite_to_html("use `code`") == "use <code>code</code>"
    assert "<i>x</i>" in markdown_lite_to_html("*x*")
    assert prepare_telegram_html("**ok**") == "<b>ok</b>"


def test_vectors():
    assert normalize_vector([1.0, 2.0], 2) == [1.0, 2.0]
    assert normalize_vector([1.0, 2.0, 3.0], 2) == [1.0, 2.0]
    assert normalize_vector([1.0], 3) == [1.0, 0.0, 0.0]
    assert vector_literal([1.0, 2.0]) == "[1.0,2.0]"
    with pytest.raises(ValueError):
        normalize_vector([1.0], 0)

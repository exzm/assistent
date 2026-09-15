from datetime import date
from decimal import Decimal

from app.services.cards import format_cards, format_item_card
from app.services.embed import build_embed_input, prepare_embed_text
from app.services.extract import (
    build_fallback_raw_text,
    normalize_extracted_fields,
    resolve_document_raw_text,
)
from app.services.rag import compose_answer, normalize_intent


def test_normalize_extracted_fields():
    data = normalize_extracted_fields(
        {
            "title": "  Bill ",
            "summary": "",
            "event_date": "2024-05-01",
            "amount": "10,5",
            "currency": "rub",
            "category": "finance",
            "tags": [" a ", "", 2],
            "entities": {"shop": "X"},
        },
        "raw",
    )
    assert data["title"] == "Bill"
    assert data["summary"] == "Bill"
    assert data["event_date"] == date(2024, 5, 1)
    assert data["amount"] == Decimal("10.5")
    assert data["currency"] == "RUB"
    assert data["tags"] == ["a", "2"]


def test_normalize_extracted_fields_fallbacks():
    data = normalize_extracted_fields({"tags": "x", "entities": "y", "category": "nope"}, "")
    assert data["title"] == "Untitled"
    assert data["tags"] == []
    assert data["entities"] == {}
    assert data["category"] == "other"


def test_document_raw_text_helpers(tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_text("x")
    assert "File:" in build_fallback_raw_text("document", filename="a.pdf")
    assert resolve_document_raw_text(
        path=path,
        mime_type="application/pdf",
        caption="c",
        existing_text="",
        pdf_text="short",
        vision_text="vision",
    ).endswith("vision")
    assert "hello" in resolve_document_raw_text(
        path=path,
        mime_type="application/pdf",
        caption="",
        existing_text="",
        pdf_text="hello " * 20,
        vision_text=None,
    )
    img = tmp_path / "a.png"
    img.write_bytes(b"1")
    assert "img" in resolve_document_raw_text(
        path=img,
        mime_type="image/png",
        caption="",
        existing_text="",
        pdf_text="",
        vision_text="img",
    )
    other = tmp_path / "a.bin"
    other.write_bytes(b"1")
    assert "File:" in resolve_document_raw_text(
        path=other,
        mime_type="application/octet-stream",
        caption="cap",
        existing_text="body",
        pdf_text="",
        vision_text=None,
    )


def test_embed_helpers():
    assert prepare_embed_text("  a   b ") == "a b"
    assert prepare_embed_text("   ") == "empty"
    assert build_embed_input("t", "s", "r").startswith("t")


def test_cards_and_rag_helpers():
    item = type(
        "I",
        (),
        {
            "id": 7,
            "title": None,
            "event_date": date(2024, 1, 1),
            "amount": "12.5",
            "currency": "USD",
            "category": "finance",
            "tags": ["a", "b"],
            "summary": "sum",
        },
    )()
    card = format_item_card(item)
    assert "#7" in card
    assert "<b>#7</b>" in card
    assert "Сумма:" in card
    assert format_cards([]) == "Источники не найдены."
    assert "#7" in format_cards([item])
    intent = normalize_intent(
        {
            "rewritten_query": "oil",
            "event_date_from": "2024-01-01",
            "min_amount": "10",
            "category": "auto_service",
        },
        "q",
    )
    assert intent["rewritten_query"] == "oil"
    composed = compose_answer("ans **bold**", [item])
    assert "<b>bold</b>" in composed
    assert "Карточки:" in composed

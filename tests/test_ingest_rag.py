from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.payload import PendingPayload
from app.services import ingest, rag
from tests.conftest import make_chat_response, make_embed_response, make_item


@pytest.mark.asyncio
async def test_extract_pdf_and_preview(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not-pdf")
    assert ingest.extract_pdf_text(bad) == ""

    with patch("app.services.ingest.convert_from_path", create=True):
        with patch("pdf2image.convert_from_path", side_effect=RuntimeError("x")):
            assert ingest.render_pdf_preview(bad) is None

    class FakeImage:
        def save(self, path, fmt):
            Path(path).write_bytes(b"img")

    with patch("pdf2image.convert_from_path", return_value=[FakeImage()]):
        preview = ingest.render_pdf_preview(bad)
        assert preview is not None
        assert preview.exists()

    with patch("pdf2image.convert_from_path", return_value=[]):
        assert ingest.render_pdf_preview(bad) is None


@pytest.mark.asyncio
async def test_resolve_raw_text_branches(tmp_path, settings):
    assert await ingest.resolve_raw_text(PendingPayload(source_type="text", text="hi"), None) == "hi"

    voice = tmp_path / "v.ogg"
    voice.write_bytes(b"1")
    with patch("app.services.stt.transcribe_audio", AsyncMock(return_value="said")):
        assert "said" in await ingest.resolve_raw_text(
            PendingPayload(source_type="voice", caption="c"), voice
        )

    photo = tmp_path / "p.jpg"
    photo.write_bytes(b"1")
    with patch("app.services.vision.describe_image", AsyncMock(return_value="seen")):
        assert "seen" in await ingest.resolve_raw_text(PendingPayload(source_type="photo"), photo)

    pdf = tmp_path / "d.pdf"
    pdf.write_bytes(b"1")
    with (
        patch("app.services.ingest.extract_pdf_text", return_value="short"),
        patch("app.services.ingest.render_pdf_preview", return_value=photo),
        patch("app.services.vision.describe_image", AsyncMock(return_value="from-image")),
    ):
        text = await ingest.resolve_raw_text(PendingPayload(source_type="document"), pdf)
        assert "from-image" in text

    img_doc = tmp_path / "i.png"
    img_doc.write_bytes(b"1")
    with patch("app.services.vision.describe_image", AsyncMock(return_value="imgdoc")):
        text = await ingest.resolve_raw_text(
            PendingPayload(source_type="document", mime_type="image/png"), img_doc
        )
        assert "imgdoc" in text

    other = tmp_path / "f.bin"
    other.write_bytes(b"1")
    text = await ingest.resolve_raw_text(
        PendingPayload(source_type="document", mime_type="application/zip", caption="z"),
        other,
    )
    assert "File:" in text

    assert "forward" in await ingest.resolve_raw_text(
        PendingPayload(source_type="forward", caption="cap"), other
    )


@pytest.mark.asyncio
async def test_ingest_payload(settings):
    session = MagicMock()
    payload = PendingPayload(source_type="text", text="Changed oil", telegram_message_id=1)
    with (
        patch("app.services.extract.extract_fields", AsyncMock(return_value={
            "title": "Oil",
            "summary": "Oil",
            "event_date": None,
            "amount": None,
            "currency": None,
            "category": "auto_service",
            "tags": [],
            "entities": {},
        })),
        patch("app.services.embed.embed_text", AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])),
        patch("app.db.repository.create_item", AsyncMock(return_value=make_item())) as create,
    ):
        item = await ingest.ingest_payload(session, payload)
        assert item.id == 1
        assert create.await_args.kwargs["event_date"] == date.today()

    payload = PendingPayload(source_type="voice", file_bytes=b"abc", file_ext="ogg")
    with (
        patch("app.services.storage.save_bytes", AsyncMock(return_value="/tmp/a.ogg")),
        patch("app.services.ingest.resolve_raw_text", AsyncMock(return_value="voice text")),
        patch("app.services.extract.extract_fields", AsyncMock(return_value={
            "title": "V",
            "summary": "V",
            "event_date": date(2024, 1, 1),
            "amount": None,
            "currency": None,
            "category": "note",
            "tags": [],
            "entities": {},
        })),
        patch("app.services.embed.embed_text", AsyncMock(return_value=[1, 0, 0, 0])),
        patch("app.db.repository.create_item", AsyncMock(return_value=make_item(id=2))),
    ):
        item = await ingest.ingest_payload(session, payload)
        assert item.id == 2


@pytest.mark.asyncio
async def test_rag_answer_paths(settings):
    session = MagicMock()
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            make_chat_response('{"rewritten_query":"oil","category":"auto_service"}'),
            make_chat_response("You changed oil on #1"),
        ]
    )
    client.embeddings.create = AsyncMock(return_value=make_embed_response([1, 0, 0, 0]))

    item = make_item(event_date=date(2024, 1, 1), amount=Decimal("10"), currency="USD")
    with patch(
        "app.db.repository.search_similar",
        AsyncMock(side_effect=[[], [item]]),
    ):
        answer, items = await rag.answer_question(
            session, "when oil?", client=client, settings=settings
        )
        assert "Cards:" in answer
        assert items == [item]

    with patch("app.db.repository.search_similar", AsyncMock(return_value=[])):
        answer, items = await rag.answer_question(
            session, "missing", client=client, settings=settings
        )
        assert items == []
        assert "No matching" in answer


@pytest.mark.asyncio
async def test_materialize_query_text():
    from app.services.query_text import is_audio_payload, is_image_payload, materialize_query_text

    assert await materialize_query_text(PendingPayload(source_type="text", text="q")) == "q"
    assert await materialize_query_text(PendingPayload(source_type="text")) == ""
    assert is_audio_payload(PendingPayload(source_type="voice"))
    assert is_image_payload(PendingPayload(source_type="photo"))

    with patch("app.services.stt.transcribe_audio", AsyncMock(return_value="voice-q")):
        text = await materialize_query_text(
            PendingPayload(source_type="voice", file_bytes=b"1", file_ext="ogg")
        )
        assert text == "voice-q"

    with patch("app.services.vision.describe_image", AsyncMock(return_value="img-q")):
        text = await materialize_query_text(
            PendingPayload(source_type="photo", file_bytes=b"1", file_ext="jpg")
        )
        assert text == "img-q"

    assert (
        await materialize_query_text(
            PendingPayload(source_type="document", file_bytes=b"1", file_ext="bin")
        )
        == ""
    )

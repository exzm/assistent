from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import embed, extract, stt, storage, vision
from app.services.download import download_telegram_file
from helpers import make_chat_response, make_embed_response


@pytest.mark.asyncio
async def test_embed_text_with_and_without_dimensions(settings):
    client = MagicMock()
    client.embeddings.create = AsyncMock(
        side_effect=[
            Exception("no dims"),
            make_embed_response([1.0, 2.0, 3.0, 4.0, 5.0]),
        ]
    )
    vector = await embed.embed_text("hello", client=client, settings=settings)
    assert len(vector) == 4

    client.embeddings.create = AsyncMock(return_value=make_embed_response([1.0]))
    vector = await embed.embed_text("hello", client=client, settings=settings)
    assert vector == [1.0, 0.0, 0.0, 0.0]


@pytest.mark.asyncio
async def test_extract_fields(settings):
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=make_chat_response('{"title":"T","category":"note","tags":["x"]}')
    )
    fields = await extract.extract_fields("body", "text", client=client, settings=settings)
    assert fields["title"] == "T"
    assert fields["category"] == "note"


@pytest.mark.asyncio
async def test_stt_and_vision(tmp_path, settings):
    audio = tmp_path / "a.ogg"
    audio.write_bytes(b"abc")
    client = MagicMock()
    client.audio.transcriptions.create = AsyncMock(return_value=SimpleNamespace(text=" hi "))
    assert await stt.transcribe_audio(audio, client=client, settings=settings) == "hi"

    image = tmp_path / "a.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    client.chat.completions.create = AsyncMock(
        side_effect=[Exception("fail"), make_chat_response("ocr text")]
    )
    text = await vision.describe_image(image, caption="cap", client=client, settings=settings)
    assert text == "ocr text"
    assert vision.image_to_data_url(image).startswith("data:image/")


@pytest.mark.asyncio
async def test_storage_and_download(settings, tmp_path):
    path = storage.build_storage_path(
        ".txt",
        settings=settings,
        now=datetime(2024, 2, 3, tzinfo=UTC),
        uuid_factory=lambda: SimpleNamespace(hex="deadbeef"),
    )
    assert path.name == "deadbeef.txt"
    saved = await storage.save_bytes(b"data", "bin", settings=settings)
    assert Path(saved).read_bytes() == b"data"

    message = MagicMock()
    buffer_holder = {}

    async def fake_download(*, file, destination):
        destination.write(b"file")
        buffer_holder["ok"] = True

    message.bot.download = fake_download
    assert await download_telegram_file(message, "fid") == b"file"

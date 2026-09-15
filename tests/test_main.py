from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import main, run_bot


@pytest.mark.asyncio
async def test_run_bot(settings):
    bot = MagicMock()
    dp = MagicMock()
    dp.start_polling = AsyncMock()
    with (
        patch("app.main.ensure_files_dir") as ensure,
        patch("app.main.wait_for_db", AsyncMock()) as wait,
        patch("app.main.Bot", return_value=bot),
        patch("app.main.create_dispatcher", return_value=dp),
    ):
        await run_bot(settings)
        ensure.assert_called_once()
        wait.assert_awaited()
        dp.start_polling.assert_awaited_with(bot)


def test_main_entrypoint():
    with patch("app.main.asyncio.run") as run:
        main()
        run.assert_called_once()

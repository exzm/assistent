# Helper Bot

Personal Telegram memory assistant. Send photos, PDFs, voice notes, text, and forwards.
The bot extracts structured facts with inexpensive LLMs via [ProxyAPI](https://proxyapi.ru),
stores originals on disk, indexes embeddings in Postgres/`pgvector`, and answers questions
with source cards.

## Features

- Single-user whitelist (`TELEGRAM_USER_ID`)
- Inline actions: **Save** / **This is a question** / **Cancel**
- Vision OCR, speech-to-text, JSON field extraction, embeddings, RAG answers
- Original file storage + `/get <id>`
- Docker Compose deployment (USA VPS friendly for Telegram access)

## Architecture

```text
Telegram → aiogram bot → Save/Ask buttons
                │
                ├─ Save → STT/Vision/Extract/Embed → Postgres + files
                └─ Ask  → Embed + hybrid retrieval → LLM answer + cards
```

## Quick start

### 1. Configure

```bash
cp .env.example .env
```

Required values:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_USER_ID` | Your numeric Telegram id |
| `PROXYAPI_API_KEY` | API key from [proxyapi.ru](https://proxyapi.ru) |

### 2. Run with Docker

```bash
docker compose up -d --build
docker compose logs -f bot
```

Then send `/start` to the bot from your whitelisted account.

### 3. Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export PYTHONPATH=bot
pytest --cov=app --cov-report=term-missing
```

## Commands

| Command | Description |
|---|---|
| `/start` | Help |
| `/recent` | Latest saved records |
| `/get <id>` | Record card + original file |
| `/ask <question>` | Ask immediately without buttons |

## Default models (ProxyAPI)

| Role | Model |
|---|---|
| Vision | `inclusionai/ling-3.0-flash-vl` |
| STT | `openai/gpt-4o-mini-transcribe` |
| Embeddings | `qwen/qwen3-embedding-8b` (`EMBED_DIMENSIONS=1024`) |
| Extract | `z-ai/glm-5.3-flash` |
| Chat / RAG | `deepseek/deepseek-v4.1-flash` |

## Project layout

```text
helper-bot/
  bot/app/           # application package
  tests/             # unit tests (100% coverage target)
  db/init/           # Postgres schema
  docker-compose.yml
  pyproject.toml
```

## Testing

```bash
pytest --cov=app --cov-report=term-missing
```

Coverage is enforced at **100%** via `pyproject.toml`.

## Security notes

- Never commit `.env`
- Rotate keys if they leak into chat/logs
- Whitelist blocks every non-owner Telegram account

## License

MIT — see [LICENSE](LICENSE).

# Helper Bot — личный Telegram memory-ассистент

Бот принимает фото, PDF, голос, заметки и пересланные сообщения, прогоняет через ProxyAPI (дешёвые LLM), сохраняет оригинал + структурированные поля + эмбеддинги в Postgres/pgvector и отвечает на вопросы с карточками найденных записей.

## Возможности

- Whitelist по твоему Telegram user id
- После каждого сообщения кнопки: **Сохранить** / **Это вопрос** / **Отмена**
- Хранение оригиналов файлов на диске
- RAG-ответы + карточки `#id`
- Команды: `/start`, `/recent`, `/get <id>`, `/ask <вопрос>`

## Быстрый старт (Docker на usnpi.com)

1. Скопируй конфиг:

```bash
cp .env.example .env
```

2. Заполни в `.env`:

- `TELEGRAM_BOT_TOKEN` — от [@BotFather](https://t.me/BotFather)
- `TELEGRAM_USER_ID` — твой id ([@userinfobot](https://t.me/userinfobot))
- `PROXYAPI_API_KEY` — ключ с [proxyapi.ru](https://proxyapi.ru)

3. Запуск:

```bash
docker compose up -d --build
docker compose logs -f bot
```

4. Напиши боту `/start` из своего аккаунта.

## Структура

```
helper-bot/
  docker-compose.yml   # bot + postgres/pgvector
  db/init/             # SQL schema
  data/files/          # оригиналы (volume)
  bot/app/             # код бота
```

## Модели ProxyAPI (по умолчанию)

| Назначение | Модель |
|---|---|
| Vision / OCR | `inclusionai/ling-3.0-flash-vl` |
| STT | `openai/gpt-4o-mini-transcribe` |
| Embeddings | `qwen/qwen3-embedding-8b` |
| Extract JSON | `z-ai/glm-5.3-flash` |
| Ответы | `deepseek/deepseek-v4.1-flash` |

Меняются через переменные `MODEL_*` в `.env`.

## Заметки

- Режим long polling — отдельный домен/SSL не нужны.
- `.env` не коммитится.
- Если размер эмбеддинга модели другой — поправь `EMBED_DIMENSIONS` и `vector(N)` в `db/init/01_schema.sql` и `bot/app/db/models.py` (нужен чистый volume БД). По умолчанию 1024 (MRL у Qwen3 + лимит HNSW в pgvector).

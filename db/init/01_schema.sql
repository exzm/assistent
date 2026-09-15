CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS items (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_type     TEXT NOT NULL,
    telegram_message_id BIGINT,
    forward_from    TEXT,
    file_path       TEXT,
    mime_type       TEXT,
    raw_text        TEXT,
    title           TEXT,
    summary         TEXT,
    event_date      DATE,
    amount          NUMERIC(14, 2),
    currency        TEXT,
    category        TEXT,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    entities        JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding       vector(1024)
);

CREATE INDEX IF NOT EXISTS items_event_date_idx ON items (event_date);
CREATE INDEX IF NOT EXISTS items_amount_idx ON items (amount);
CREATE INDEX IF NOT EXISTS items_category_idx ON items (category);
CREATE INDEX IF NOT EXISTS items_tags_gin_idx ON items USING GIN (tags);
CREATE INDEX IF NOT EXISTS items_created_at_idx ON items (created_at DESC);

CREATE INDEX IF NOT EXISTS items_embedding_hnsw_idx
    ON items USING hnsw (embedding vector_cosine_ops);

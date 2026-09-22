"""SQLite data layer.

Uses plain sqlite3 so the schema can later migrate to PostgreSQL with minimal
changes (no ORM lock-in for the MVP).
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id            TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,          -- audio | subtitle | vocabulary | cover
    original_name TEXT NOT NULL,
    stored_path   TEXT NOT NULL,          -- relative to project root, or absolute
    content_type  TEXT,
    size_bytes    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS podcasts (
    id              TEXT PRIMARY KEY,
    source_key      TEXT UNIQUE,          -- used by the seed script for idempotency
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    audio_file_id   TEXT NOT NULL REFERENCES files(id),
    subtitle_file_id TEXT REFERENCES files(id),
    cover_file_id   TEXT REFERENCES files(id),
    vocabulary_file_id TEXT REFERENCES files(id),
    subtitle_format TEXT NOT NULL,        -- srt | vtt | transcript-docx | transcript-pdf | transcript-txt
    duration        REAL NOT NULL DEFAULT 0,
    segment_count   INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS segments (
    id         TEXT PRIMARY KEY,
    podcast_id TEXT NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
    idx        INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time   REAL NOT NULL,
    text       TEXT NOT NULL,
    speaker    TEXT
);
CREATE INDEX IF NOT EXISTS idx_segments_podcast ON segments(podcast_id, idx);

CREATE TABLE IF NOT EXISTS vocabulary_entries (
    id              TEXT PRIMARY KEY,
    podcast_id      TEXT NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
    word            TEXT NOT NULL,
    base_form       TEXT,
    persian_meaning TEXT,
    english_meaning TEXT,
    part_of_speech  TEXT,
    notes           TEXT,
    example         TEXT,
    row_number      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_vocab_podcast ON vocabulary_entries(podcast_id);
"""


def new_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: Path | None = None) -> None:
    config.ensure_data_dirs()
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


def rows_to_dicts(rows: Iterator[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]

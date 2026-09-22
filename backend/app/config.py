"""Application configuration and shared paths."""
from __future__ import annotations

import os
from pathlib import Path

# backend/ directory (this file lives in backend/app/)
BACKEND_DIR = Path(__file__).resolve().parent.parent
# Project root (contains the original podcast source files)
PROJECT_ROOT = Path(os.environ.get("PODCAST_PROJECT_ROOT", BACKEND_DIR.parent))

DATA_DIR = Path(os.environ.get("PODCAST_DATA_DIR", BACKEND_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = Path(os.environ.get("PODCAST_DB_PATH", DATA_DIR / "app.db"))
SEED_MANIFEST_PATH = Path(
    os.environ.get("PODCAST_SEED_MANIFEST", BACKEND_DIR / "seed_manifest.json")
)
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".txt", ".docx", ".pdf"}
VOCABULARY_EXTENSIONS = {".xlsx"}
COVER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

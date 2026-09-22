"""API-level tests with FastAPI TestClient (fresh temp database)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """FastAPI client bound to a temporary database."""
    from app import config

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "SEED_MANIFEST_PATH", tmp_path / "missing_manifest.json")

    # import after patching so startup seed doesn't touch the real DB
    from app.db import init_db
    init_db()

    from fastapi.testclient import TestClient
    from app.main import app

    # startup only re-inits the (already patched) DB and skips missing manifest
    with TestClient(app) as c:
        yield c


def _upload(client, endpoint: str, filename: str, content: bytes, content_type: str = "application/octet-stream"):
    return client.post(
        endpoint,
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


class TestHealth:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestPodcastList:
    def test_empty_library(self, client):
        r = client.get("/api/podcasts")
        assert r.status_code == 200
        assert r.json() == []


class TestUploadValidation:
    def test_rejects_bad_audio_extension(self, client):
        r = _upload(client, "/api/uploads/audio", "song.exe", b"MZ")
        assert r.status_code == 400
        assert "Unsupported audio" in r.json()["detail"]

    def test_rejects_bad_subtitle_extension(self, client):
        r = _upload(client, "/api/uploads/subtitles", "notes.doc", b"x")
        assert r.status_code == 400

    def test_rejects_bad_vocabulary_extension(self, client):
        r = _upload(client, "/api/uploads/vocabulary", "vocab.csv", b"a,b")
        assert r.status_code == 400

    def test_invalid_audio_content(self, client):
        r = _upload(client, "/api/uploads/audio", "fake.mp3", b"not really an mp3")
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_invalid_excel_content(self, client):
        r = _upload(client, "/api/uploads/vocabulary", "fake.xlsx", b"not an excel file")
        assert r.status_code == 400


class TestPodcastValidation:
    def test_create_requires_title(self, client):
        r = client.post("/api/podcasts", json={"audioFileId": "x", "subtitleFileId": "y"})
        assert r.status_code == 422  # pydantic min_length

    def test_create_missing_audio_file(self, client):
        r = client.post(
            "/api/podcasts",
            json={"title": "T", "audioFileId": "nope", "subtitleFileId": "nope2"},
        )
        assert r.status_code == 400

    def test_get_missing_podcast(self, client):
        r = client.get("/api/podcasts/does-not-exist")
        assert r.status_code == 404

    def test_delete_missing_podcast(self, client):
        r = client.delete("/api/podcasts/does-not-exist")
        assert r.status_code == 404


class TestFileEndpoint:
    def test_missing_file_404(self, client):
        r = client.get("/api/files/nope/content")
        assert r.status_code == 404

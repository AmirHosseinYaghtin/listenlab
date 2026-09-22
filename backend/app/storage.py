"""File storage abstraction.

All file paths are stored relative to the project root when possible so the
database stays portable. Original source podcast files are referenced in
place (never copied or modified); uploads are written under backend/data/uploads.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from . import config
from .db import get_connection, new_id, now_iso


def _relative_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(config.PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def resolve_stored_path(stored_path: str) -> Path:
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return (config.PROJECT_ROOT / p).resolve()


class StorageError(Exception):
    """Human-readable storage problem."""


def register_file(
    *,
    kind: str,
    path: Path,
    original_name: str | None = None,
    content_type: str | None = None,
    conn=None,
) -> dict:
    """Register an existing file (upload result or original source file)."""
    if not path.exists():
        raise StorageError(f"File not found: {path}")
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        file_id = new_id()
        row = {
            "id": file_id,
            "kind": kind,
            "original_name": original_name or path.name,
            "stored_path": _relative_to_root(path),
            "content_type": content_type,
            "size_bytes": path.stat().st_size,
            "created_at": now_iso(),
        }
        conn.execute(
            "INSERT INTO files (id, kind, original_name, stored_path, content_type, size_bytes, created_at)"
            " VALUES (:id, :kind, :original_name, :stored_path, :content_type, :size_bytes, :created_at)",
            row,
        )
        if own_conn:
            conn.commit()
        return row
    finally:
        if own_conn:
            conn.close()


def find_file_by_path(stored_path: str, conn=None) -> dict | None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM files WHERE stored_path = ?", (stored_path,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


def get_file(file_id: str, conn=None) -> dict | None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        return dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


def save_upload(
    *,
    kind: str,
    filename: str,
    stream: BinaryIO,
    content_type: str | None = None,
    conn=None,
) -> dict:
    """Write an uploaded stream to the uploads directory and register it."""
    config.ensure_data_dirs()
    safe_name = Path(filename).name.replace("\\", "_").replace("/", "_")
    file_id = new_id()
    target = config.UPLOAD_DIR / f"{file_id}_{safe_name}"
    with open(target, "wb") as out:
        shutil.copyfileobj(stream, out)
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        existing = find_file_by_path(_relative_to_root(target), conn=conn)
        if existing:
            return existing
        row = {
            "id": file_id,
            "kind": kind,
            "original_name": safe_name,
            "stored_path": _relative_to_root(target),
            "content_type": content_type,
            "size_bytes": target.stat().st_size,
            "created_at": now_iso(),
        }
        conn.execute(
            "INSERT INTO files (id, kind, original_name, stored_path, content_type, size_bytes, created_at)"
            " VALUES (:id, :kind, :original_name, :stored_path, :content_type, :size_bytes, :created_at)",
            row,
        )
        if own_conn:
            conn.commit()
        return row
    finally:
        if own_conn:
            conn.close()

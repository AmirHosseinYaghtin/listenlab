"""Upload endpoints: audio, subtitles, vocabulary, cover images.

Each endpoint validates the file, stores it, and returns a preview so the
create/edit wizard can show the user what was detected before saving.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from .. import config
from ..services.audio_meta import AudioProbeError, probe_audio
from ..services.excel_parser import ExcelParseError, import_vocabulary_excel
from ..services.subtitle_parser import SubtitleParseError, parse_subtitle_file
from ..storage import StorageError, save_upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

CHUNK = 1024 * 1024


def _validate_extension(filename: str, allowed: set[str], kind_label: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported {kind_label} file type '{suffix or filename}'. "
                f"Accepted types: {', '.join(sorted(allowed))}."
            ),
        )
    return suffix


def _store(upload: UploadFile, kind: str) -> dict:
    try:
        # stream to disk through the storage abstraction
        return save_upload(kind=kind, filename=upload.filename or "upload", stream=upload.file,
                           content_type=upload.content_type)
    except (StorageError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not save the file: {exc}") from exc


@router.post("/audio")
def upload_audio(file: UploadFile = ...):
    _validate_extension(file.filename or "", config.AUDIO_EXTENSIONS, "audio")
    row = _store(file, "audio")
    path = Path(row["stored_path"])
    if not path.is_absolute():
        from ..config import PROJECT_ROOT
        path = PROJECT_ROOT / path
    try:
        info = probe_audio(path)
    except AudioProbeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "fileId": row["id"],
        "originalName": row["original_name"],
        "duration": info["duration"],
        "sizeBytes": row["size_bytes"],
    }


@router.post("/subtitles")
def upload_subtitles(file: UploadFile = ...):
    suffix = _validate_extension(file.filename or "", config.SUBTITLE_EXTENSIONS, "subtitle")
    row = _store(file, "subtitle")
    from ..config import PROJECT_ROOT
    path = Path(row["stored_path"])
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        result = parse_subtitle_file(path, duration=None)
    except SubtitleParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result.segments:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No subtitle segments could be read from {row['original_name']}. "
                "Check that the file contains timestamps."
            ),
        )
    return {
        "fileId": row["id"],
        "originalName": row["original_name"],
        "format": result.format,
        "segmentCount": len(result.segments),
        "firstSegments": result.segments[:5],
        "lastSegments": result.segments[-2:],
        "issues": [i.to_dict() for i in result.issues[:20]],
        "issueCount": len(result.issues),
    }


@router.post("/vocabulary")
def upload_vocabulary(file: UploadFile = ...):
    _validate_extension(file.filename or "", config.VOCABULARY_EXTENSIONS, "vocabulary")
    row = _store(file, "vocabulary")
    from ..config import PROJECT_ROOT
    path = Path(row["stored_path"])
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        result = import_vocabulary_excel(path)
    except ExcelParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    preview = result.preview_dict(limit=15)
    preview["fileId"] = row["id"]
    preview["originalName"] = row["original_name"]
    return preview


@router.post("/cover")
def upload_cover(file: UploadFile = ...):
    _validate_extension(file.filename or "", config.COVER_EXTENSIONS, "image")
    row = _store(file, "cover")
    return {
        "fileId": row["id"],
        "originalName": row["original_name"],
        "url": f"/api/files/{row['id']}/content",
    }

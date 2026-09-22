"""File content endpoint with HTTP Range support (needed for audio seeking)."""
from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from ..storage import get_file, resolve_stored_path

router = APIRouter(prefix="/api/files", tags=["files"])

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def _content_type(path: Path, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or fallback


@router.get("/{file_id}/content")
def read_file(file_id: str, request: Request):
    row = get_file(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")
    path = resolve_stored_path(row["stored_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="The file is missing from disk.")

    file_size = path.stat().st_size
    content_type = row.get("content_type") or _content_type(path)
    media_range = request.headers.get("range")

    base_headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{path.name}"',
        "Cache-Control": "private, max-age=3600",
    }

    if media_range:
        m = _RANGE_RE.match(media_range.strip())
        if m:
            start_s, end_s = m.group(1), m.group(2)
            if start_s == "" and end_s == "":
                raise HTTPException(status_code=416, detail="Invalid byte range.")
            if start_s == "":
                # suffix range: last N bytes
                length = int(end_s or 0)
                start = max(0, file_size - length)
                end = file_size - 1
            else:
                start = int(start_s)
                end = int(end_s) if end_s else file_size - 1
            end = min(end, file_size - 1)
            if start > end or start >= file_size:
                return Response(
                    status_code=416,
                    headers={"Content-Range": f"bytes */{file_size}"},
                )
            chunk_size = end - start + 1

            def iterator(offset=start, remaining=chunk_size):
                with open(path, "rb") as f:
                    f.seek(offset)
                    while remaining > 0:
                        data = f.read(min(64 * 1024, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            headers = {
                **base_headers,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(chunk_size),
            }
            return StreamingResponse(
                iterator(),
                status_code=206,
                media_type=content_type,
                headers=headers,
            )

    return Response(
        path.read_bytes(),
        media_type=content_type,
        headers={**base_headers, "Content-Length": str(file_size)},
    )

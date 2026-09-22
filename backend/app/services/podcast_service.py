"""Podcast domain service: CRUD + serialization for the API layer."""
from __future__ import annotations

from typing import Any

from ..db import get_connection, new_id, now_iso
from ..services.audio_meta import AudioProbeError, probe_audio
from ..services.excel_parser import ExcelParseError, import_vocabulary_excel
from ..services.subtitle_parser import SubtitleParseError, parse_subtitle_file
from ..services.vocab_matcher import annotate_segments, compile_matcher
from ..storage import get_file, register_file, resolve_stored_path


class PodcastNotFound(Exception):
    pass


class PodcastValidationError(Exception):
    pass


# ---------------------------------------------------------------------------
# serialization helpers
# ---------------------------------------------------------------------------

def _file_url(file_row: dict | None) -> str | None:
    if not file_row:
        return None
    return f"/api/files/{file_row['id']}/content"


def _podcast_row(conn, podcast_id: str) -> dict:
    row = conn.execute("SELECT * FROM podcasts WHERE id = ?", (podcast_id,)).fetchone()
    if row is None:
        raise PodcastNotFound(podcast_id)
    return dict(row)


def _segments(conn, podcast_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT idx, start_time, end_time, text, speaker FROM segments "
        "WHERE podcast_id = ? ORDER BY idx",
        (podcast_id,),
    ).fetchall()
    return [
        {
            "id": str(r["idx"]),
            "index": r["idx"],
            "startTime": r["start_time"],
            "endTime": r["end_time"],
            "text": r["text"],
            "speaker": r["speaker"],
        }
        for r in rows
    ]


def _vocabulary(conn, podcast_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT id, word, base_form, persian_meaning, english_meaning, "
        "part_of_speech, notes, example, row_number "
        "FROM vocabulary_entries WHERE podcast_id = ? ORDER BY row_number, word",
        (podcast_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "word": r["word"],
            "baseForm": r["base_form"],
            "persianMeaning": r["persian_meaning"],
            "englishMeaning": r["english_meaning"],
            "partOfSpeech": r["part_of_speech"],
            "notes": r["notes"],
            "example": r["example"],
            "rowNumber": r["row_number"],
        }
        for r in rows
    ]


def _summary(conn, row: dict) -> dict[str, Any]:
    audio = get_file(row["audio_file_id"], conn=conn)
    cover = get_file(row["cover_file_id"], conn=conn) if row.get("cover_file_id") else None
    vocab_count = conn.execute(
        "SELECT COUNT(*) AS c FROM vocabulary_entries WHERE podcast_id = ?",
        (row["id"],),
    ).fetchone()["c"]
    return {
        "id": row["id"],
        "sourceKey": row.get("source_key"),
        "title": row["title"],
        "description": row["description"],
        "duration": row["duration"],
        "segmentCount": row["segment_count"],
        "vocabCount": vocab_count,
        "subtitleFormat": row["subtitle_format"],
        "hasVocabularyFile": bool(row.get("vocabulary_file_id")),
        "coverUrl": _file_url(cover),
        "audioName": audio["original_name"] if audio else None,
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def list_podcasts() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM podcasts ORDER BY created_at"
        ).fetchall()
        return [_summary(conn, dict(r)) for r in rows]


def get_podcast(podcast_id: str) -> dict:
    with get_connection() as conn:
        row = _podcast_row(conn, podcast_id)
        summary = _summary(conn, row)
        audio = get_file(row["audio_file_id"], conn=conn)
        cover = get_file(row["cover_file_id"], conn=conn) if row.get("cover_file_id") else None
        subtitle = get_file(row["subtitle_file_id"], conn=conn) if row.get("subtitle_file_id") else None
        vocab_file = get_file(row["vocabulary_file_id"], conn=conn) if row.get("vocabulary_file_id") else None

        vocabulary = _vocabulary(conn, podcast_id)
        segments = _segments(conn, podcast_id)
        annotated = annotate_segments(segments, vocabulary)

        return {
            **summary,
            "audioUrl": _file_url(audio),
            "audioName": audio["original_name"] if audio else None,
            "coverUrl": _file_url(cover),
            "subtitleName": subtitle["original_name"] if subtitle else None,
            "vocabularyFileName": vocab_file["original_name"] if vocab_file else None,
            "segments": annotated,
            "vocabulary": vocabulary,
        }


def create_podcast(payload: dict) -> dict:
    """Create a podcast from already-uploaded file ids."""
    title = (payload.get("title") or "").strip()
    if not title:
        raise PodcastValidationError("A podcast title is required.")
    audio_id = payload.get("audioFileId")
    if not audio_id:
        raise PodcastValidationError("An audio file is required.")
    audio = get_file(audio_id)
    if not audio or audio["kind"] != "audio":
        raise PodcastValidationError("The audio file could not be found. Please upload it again.")
    subtitle_id = payload.get("subtitleFileId")
    if not subtitle_id:
        raise PodcastValidationError("A subtitle/transcript file is required.")
    subtitle = get_file(subtitle_id)
    if not subtitle or subtitle["kind"] != "subtitle":
        raise PodcastValidationError("The subtitle file could not be found. Please upload it again.")

    audio_path = resolve_stored_path(audio["stored_path"])
    subtitle_path = resolve_stored_path(subtitle["stored_path"])

    try:
        audio_info = probe_audio(audio_path)
    except AudioProbeError as exc:
        raise PodcastValidationError(str(exc)) from exc
    try:
        subtitle_result = parse_subtitle_file(subtitle_path, audio_info["duration"])
    except SubtitleParseError as exc:
        raise PodcastValidationError(str(exc)) from exc
    if not subtitle_result.segments:
        raise PodcastValidationError(
            f"No readable subtitle segments were found in {subtitle['original_name']}."
        )

    vocab_entries: list[dict] = []
    vocab_file_id = payload.get("vocabularyFileId") or None
    if vocab_file_id:
        vocab_file = get_file(vocab_file_id)
        if not vocab_file or vocab_file["kind"] != "vocabulary":
            raise PodcastValidationError("The vocabulary file could not be found. Please upload it again.")
        try:
            result = import_vocabulary_excel(
                resolve_stored_path(vocab_file["stored_path"]),
                payload.get("vocabularyMapping"),
            )
        except ExcelParseError as exc:
            raise PodcastValidationError(str(exc)) from exc
        vocab_entries = [e.to_dict() for e in result.entries]

    cover_file_id = payload.get("coverFileId") or None
    if cover_file_id:
        cover = get_file(cover_file_id)
        if not cover or cover["kind"] != "cover":
            raise PodcastValidationError("The cover image could not be found.")

    podcast_id = new_id()
    now = now_iso()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO podcasts
               (id, source_key, title, description, audio_file_id, subtitle_file_id,
                cover_file_id, vocabulary_file_id, subtitle_format, duration,
                segment_count, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                podcast_id,
                payload.get("sourceKey"),
                title,
                (payload.get("description") or "").strip(),
                audio_id,
                subtitle_id,
                cover_file_id,
                vocab_file_id,
                subtitle_result.format,
                audio_info["duration"],
                len(subtitle_result.segments),
                now,
                now,
            ),
        )
        _insert_segments(conn, podcast_id, subtitle_result.segments)
        _insert_vocabulary(conn, podcast_id, vocab_entries)
        conn.commit()
    return get_podcast(podcast_id)


def _insert_segments(conn, podcast_id: str, segments: list[dict]) -> None:
    conn.executemany(
        """INSERT INTO segments (id, podcast_id, idx, start_time, end_time, text, speaker)
           VALUES (?,?,?,?,?,?,?)""",
        [
            (new_id(), podcast_id, s["index"], s["startTime"], s["endTime"], s["text"], s["speaker"])
            for s in segments
        ],
    )


def _insert_vocabulary(conn, podcast_id: str, entries: list[dict]) -> None:
    conn.executemany(
        """INSERT INTO vocabulary_entries
           (id, podcast_id, word, base_form, persian_meaning, english_meaning,
            part_of_speech, notes, example, row_number)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        [
            (
                new_id(),
                podcast_id,
                e["word"],
                e.get("baseForm"),
                e.get("persianMeaning"),
                e.get("englishMeaning"),
                e.get("partOfSpeech"),
                e.get("notes"),
                e.get("example"),
                e.get("rowNumber"),
            )
            for e in entries
        ],
    )


def update_podcast(podcast_id: str, payload: dict) -> dict:
    """Update metadata and optionally replace audio/subtitles/vocabulary/cover."""
    with get_connection() as conn:
        row = _podcast_row(conn, podcast_id)

        title = payload.get("title", row["title"])
        if isinstance(title, str):
            title = title.strip()
            if not title:
                raise PodcastValidationError("A podcast title is required.")
        description = payload.get("description", row["description"])
        if isinstance(description, str):
            description = description.strip()

        audio_file_id = row["audio_file_id"]
        subtitle_file_id = row["subtitle_file_id"]
        cover_file_id = row["cover_file_id"]
        vocabulary_file_id = row["vocabulary_file_id"]
        duration = row["duration"]
        subtitle_format = row["subtitle_format"]
        segment_count = row["segment_count"]

        needs_resync = False

        if payload.get("audioFileId"):
            audio = get_file(payload["audioFileId"], conn=conn)
            if not audio or audio["kind"] != "audio":
                raise PodcastValidationError("The new audio file could not be found.")
            try:
                duration = probe_audio(resolve_stored_path(audio["stored_path"]))["duration"]
            except AudioProbeError as exc:
                raise PodcastValidationError(str(exc)) from exc
            audio_file_id = audio["id"]
            needs_resync = True

        if payload.get("subtitleFileId"):
            subtitle = get_file(payload["subtitleFileId"], conn=conn)
            if not subtitle or subtitle["kind"] != "subtitle":
                raise PodcastValidationError("The new subtitle file could not be found.")
            try:
                result = parse_subtitle_file(resolve_stored_path(subtitle["stored_path"]), duration)
            except SubtitleParseError as exc:
                raise PodcastValidationError(str(exc)) from exc
            if not result.segments:
                raise PodcastValidationError(
                    f"No readable subtitle segments were found in {subtitle['original_name']}."
                )
            subtitle_file_id = subtitle["id"]
            subtitle_format = result.format
            segment_count = len(result.segments)
            conn.execute("DELETE FROM segments WHERE podcast_id = ?", (podcast_id,))
            _insert_segments(conn, podcast_id, result.segments)

        if payload.get("coverFileId"):
            cover = get_file(payload["coverFileId"], conn=conn)
            if not cover or cover["kind"] != "cover":
                raise PodcastValidationError("The cover image could not be found.")
            cover_file_id = cover["id"]

        if payload.get("vocabularyFileId"):
            vocab_file = get_file(payload["vocabularyFileId"], conn=conn)
            if not vocab_file or vocab_file["kind"] != "vocabulary":
                raise PodcastValidationError("The vocabulary file could not be found.")
            try:
                result = import_vocabulary_excel(
                    resolve_stored_path(vocab_file["stored_path"]),
                    payload.get("vocabularyMapping"),
                )
            except ExcelParseError as exc:
                raise PodcastValidationError(str(exc)) from exc
            vocabulary_file_id = vocab_file["id"]
            conn.execute(
                "DELETE FROM vocabulary_entries WHERE podcast_id = ?", (podcast_id,)
            )
            _insert_vocabulary(conn, podcast_id, [e.to_dict() for e in result.entries])

        if needs_resync and not payload.get("subtitleFileId"):
            # audio changed but subtitles kept: refresh last-segment end times
            conn.execute("DELETE FROM segments WHERE podcast_id = ?", (podcast_id,))
            result = parse_subtitle_file(
                resolve_stored_path(
                    get_file(subtitle_file_id, conn=conn)["stored_path"]
                ),
                duration,
            )
            segment_count = len(result.segments)
            subtitle_format = result.format
            _insert_segments(conn, podcast_id, result.segments)

        conn.execute(
            """UPDATE podcasts SET title=?, description=?, audio_file_id=?,
               subtitle_file_id=?, cover_file_id=?, vocabulary_file_id=?,
               subtitle_format=?, duration=?, segment_count=?, updated_at=?
               WHERE id=?""",
            (
                title,
                description,
                audio_file_id,
                subtitle_file_id,
                cover_file_id,
                vocabulary_file_id,
                subtitle_format,
                duration,
                segment_count,
                now_iso(),
                podcast_id,
            ),
        )
        conn.commit()
    return get_podcast(podcast_id)


def delete_podcast(podcast_id: str) -> None:
    with get_connection() as conn:
        _podcast_row(conn, podcast_id)
        conn.execute("DELETE FROM podcasts WHERE id = ?", (podcast_id,))
        conn.commit()


def vocabulary_preview(payload: dict) -> dict:
    """Parse an uploaded vocabulary file and return headers/mapping/preview."""
    file_id = payload.get("fileId")
    if not file_id:
        raise PodcastValidationError("No vocabulary file was provided.")
    file_row = get_file(file_id)
    if not file_row:
        raise PodcastValidationError("The vocabulary file could not be found.")
    try:
        result = import_vocabulary_excel(
            resolve_stored_path(file_row["stored_path"]),
            payload.get("mapping"),
        )
    except ExcelParseError as exc:
        raise PodcastValidationError(str(exc)) from exc
    return result.preview_dict()


def matching_stats(podcast_id: str) -> dict[str, Any]:
    """How many transcript hits each vocabulary expression has (debug/teacher aid)."""
    with get_connection() as conn:
        _podcast_row(conn, podcast_id)
        vocabulary = _vocabulary(conn, podcast_id)
        segments = _segments(conn, podcast_id)
    regex, entries = compile_matcher(vocabulary)
    counts: dict[str, int] = {}
    if regex:
        id_to_word = {e["id"]: e["word"] for e in entries}
        for seg in segments:
            from ..services.vocab_matcher import annotate_text
            for part in annotate_text(seg["text"], regex, entries):
                vid = part.get("v")
                if vid:
                    counts[vid] = counts.get(vid, 0) + 1
    return {
        "matchedTypes": len(counts),
        "totalTypes": len(vocabulary),
        "totalHits": sum(counts.values()),
        "byWord": {id_to_word.get(k, k): v for k, v in sorted(counts.items(), key=lambda kv: -kv[1])}
        if regex
        else {},
    }

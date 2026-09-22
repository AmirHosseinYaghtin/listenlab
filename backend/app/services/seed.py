"""Seed script: discovers and imports the three existing podcast datasets.

The association between audio / transcript / vocabulary files lives in
``backend/seed_manifest.json`` so filenames never need to be guessed.

Usage (from the backend/ directory, with PYTHONPATH set to backend/):
    python -m app.services.seed           # idempotent; skips already-imported podcasts
    python -m app.services.seed --force   # re-import everything (deletes existing rows)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import config
from ..db import get_connection, init_db, new_id, now_iso
from ..services.audio_meta import AudioProbeError, probe_audio
from ..services.excel_parser import ExcelParseError, import_vocabulary_excel
from ..services.subtitle_parser import SubtitleParseError, parse_subtitle_file
from ..storage import find_file_by_path, register_file


def load_manifest(path: Path | None = None) -> list[dict]:
    manifest_path = path or config.SEED_MANIFEST_PATH
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Seed manifest not found: {manifest_path}. "
            "Create it or set PODCAST_SEED_MANIFEST."
        )
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("podcasts", [])
    if not isinstance(data, list):
        raise ValueError("Seed manifest must be a list of podcast descriptors.")
    return data


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (config.PROJECT_ROOT / p).resolve()


def _register_source(kind: str, path: Path, conn) -> dict:
    rel = None
    try:
        rel = str(path.resolve().relative_to(config.PROJECT_ROOT))
    except ValueError:
        rel = str(path.resolve())
    existing = find_file_by_path(rel, conn=conn)
    if existing:
        return existing
    return register_file(kind=kind, path=path, original_name=path.name, conn=conn)


def seed(force: bool = False, manifest_path: Path | None = None) -> list[dict]:
    """Import every podcast described in the manifest. Returns summaries."""
    init_db()
    items = load_manifest(manifest_path)
    imported: list[dict] = []

    for item in items:
        source_key = item.get("sourceKey") or item.get("id")
        if not source_key:
            raise ValueError(f"Manifest entry missing sourceKey: {item}")
        audio_path = _resolve(item["audio"])
        subtitle_path = _resolve(item["subtitles"])
        vocab_path = _resolve(item.get("vocabulary") or "")

        for label, p in (("audio", audio_path), ("transcript", subtitle_path)):
            if not p.exists():
                raise FileNotFoundError(f"{label} file not found for '{source_key}': {p}")
        if item.get("vocabulary") and not vocab_path.exists():
            raise FileNotFoundError(
                f"vocabulary file not found for '{source_key}': {vocab_path}"
            )

        conn = get_connection()
        try:
            existing = conn.execute(
                "SELECT id FROM podcasts WHERE source_key = ?", (source_key,)
            ).fetchone()
            if existing and not force:
                imported.append({"sourceKey": source_key, "status": "skipped", "id": existing["id"]})
                continue
            if existing and force:
                conn.execute("DELETE FROM podcasts WHERE id = ?", (existing["id"],))

            audio_info = probe_audio(audio_path)
            subtitle_result = parse_subtitle_file(subtitle_path, audio_info["duration"])
            if not subtitle_result.segments:
                raise SubtitleParseError(
                    f"No subtitle segments found in {subtitle_path.name}"
                )

            audio_file = _register_source("audio", audio_path, conn)
            subtitle_file = _register_source("subtitle", subtitle_path, conn)
            vocab_file = None
            entries: list[dict] = []
            if vocab_path.exists():
                vocab_file = _register_source("vocabulary", vocab_path, conn)
                result = import_vocabulary_excel(vocab_path)
                entries = [e.to_dict() for e in result.entries]
                if item.get("vocabularyMapping"):
                    # manifest may override auto-mapping
                    result = import_vocabulary_excel(vocab_path, item["vocabularyMapping"])
                    entries = [e.to_dict() for e in result.entries]

            podcast_id = new_id()
            now = now_iso()
            conn.execute(
                """INSERT INTO podcasts
                   (id, source_key, title, description, audio_file_id, subtitle_file_id,
                    cover_file_id, vocabulary_file_id, subtitle_format, duration,
                    segment_count, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    podcast_id,
                    source_key,
                    item.get("title") or audio_path.stem,
                    item.get("description") or "",
                    audio_file["id"],
                    subtitle_file["id"],
                    None,
                    vocab_file["id"] if vocab_file else None,
                    subtitle_result.format,
                    audio_info["duration"],
                    len(subtitle_result.segments),
                    now,
                    now,
                ),
            )
            conn.executemany(
                """INSERT INTO segments (id, podcast_id, idx, start_time, end_time, text, speaker)
                   VALUES (?,?,?,?,?,?,?)""",
                [
                    (
                        new_id(),
                        podcast_id,
                        s["index"],
                        s["startTime"],
                        s["endTime"],
                        s["text"],
                        s["speaker"],
                    )
                    for s in subtitle_result.segments
                ],
            )
            if entries:
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
            conn.commit()
            imported.append(
                {
                    "sourceKey": source_key,
                    "status": "imported",
                    "id": podcast_id,
                    "title": item.get("title"),
                    "segments": len(subtitle_result.segments),
                    "vocabulary": len(entries),
                    "issues": len(subtitle_result.issues),
                }
            )
        finally:
            conn.close()

    return imported


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the podcast library.")
    parser.add_argument("--force", action="store_true", help="re-import even if present")
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        results = seed(force=args.force, manifest_path=args.manifest)
    except (FileNotFoundError, ValueError, SubtitleParseError, ExcelParseError, AudioProbeError) as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    for r in results:
        print(f"[{r['status']:>8}] {r.get('sourceKey')}: {r.get('title') or ''} "
              f"({r.get('segments', '-')} segments, {r.get('vocabulary', '-')} vocab)")
    print(f"Done. {sum(1 for r in results if r['status'] == 'imported')} imported, "
          f"{sum(1 for r in results if r['status'] == 'skipped')} skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

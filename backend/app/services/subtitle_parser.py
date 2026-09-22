"""Subtitle / transcript parsing.

Supported inputs:
  * .srt            – SubRip
  * .vtt            – WebVTT
  * .docx / .pdf / .txt – classroom transcript documents that embed plain
    timestamps such as ``0:08`` or ``1:02:33`` on their own lines
    (optionally followed by ``Speaker N`` label lines).

Output is always a list of ``SubtitleSegment`` dicts:
    {id, index, startTime, endTime, text, speaker}
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

TIMING_LINE_RE = re.compile(r"-->")
PLAIN_TS_RE = re.compile(r"^\s*(\d{1,3}:\d{2}(?::\d{2})?)\s*$")
SPEAKER_RE = re.compile(r"^\s*Speaker\s*#?\d+\s*$", re.IGNORECASE)


class SubtitleParseError(Exception):
    """Raised when a subtitle file cannot be parsed at all."""


@dataclass
class ParseIssue:
    line: int
    message: str

    def to_dict(self) -> dict:
        return {"line": self.line, "message": self.message}


@dataclass
class ParseResult:
    format: str
    segments: list[dict] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)


# ---------------------------------------------------------------------------
# timestamp helpers
# ---------------------------------------------------------------------------

def parse_timestamp(raw: str) -> float | None:
    """Parse ``HH:MM:SS,mmm`` / ``MM:SS.mmm`` / ``M:SS`` style timestamps.

    Returns seconds or None when the value is malformed.
    """
    raw = raw.strip()
    if not raw:
        return None
    # fraction: SRT uses "SS,mmm", VTT uses "SS.mmm"
    if "," in raw:
        raw = raw.replace(",", ".")
    # drop trailing junk (e.g. cue settings already split off by callers)
    raw = raw.split()[0] if raw.split() else raw
    parts = raw.split(":")
    if len(parts) < 2 or len(parts) > 3:
        return None
    try:
        if len(parts) == 3:
            h, m, s = (int(parts[0]), int(parts[1]), float(parts[2]))
        else:
            m, s = int(parts[0]), float(parts[1])
            h = 0
    except ValueError:
        return None
    if h < 0 or m < 0 or m > 59 or s < 0 or s >= 61:
        return None
    return h * 3600 + m * 60 + s


def _format_segments(
    raw_segments: list[tuple[float | None, float | None, str, str | None]],
    issues: list[ParseIssue],
    fmt: str,
    duration: float | None = None,
) -> list[dict]:
    """Turn (start, end, text, speaker) tuples into finalized segments."""
    cleaned: list[tuple[float, float | None, str, str | None]] = []
    for start, end, text, speaker in raw_segments:
        text = " ".join(text.split())
        if not text:
            continue
        if start is None:
            continue
        cleaned.append((start, end, text, speaker))

    segments: list[dict] = []
    for i, (start, end, text, speaker) in enumerate(cleaned):
        if end is None:
            if i + 1 < len(cleaned):
                end = cleaned[i + 1][0]
            elif duration and duration > start:
                end = duration
            else:
                end = start + max(3.0, min(12.0, len(text) * 0.08))
        if end <= start:
            # zero-length / inverted: give it a minimal readable window;
            # the player resolves ties by choosing the latest segment.
            end = start + 0.4
        segments.append(
            {
                "id": f"{i}",
                "index": i,
                "startTime": round(start, 3),
                "endTime": round(end, 3),
                "text": text,
                "speaker": speaker,
            }
        )
    return segments


# ---------------------------------------------------------------------------
# SRT
# ---------------------------------------------------------------------------

def parse_srt(content: str, duration: float | None = None) -> ParseResult:
    result = ParseResult(format="srt")
    if "\r\n" in content:
        content = content.replace("\r\n", "\n")
    blocks = re.split(r"\n\s*\n", content.strip())
    raw: list[tuple[float | None, float | None, str, str | None]] = []
    for b_i, block in enumerate(blocks):
        lines = [ln for ln in block.split("\n")]
        if not any(ln.strip() for ln in lines):
            continue
        timing_idx = next(
            (i for i, ln in enumerate(lines) if TIMING_LINE_RE.search(ln)), None
        )
        if timing_idx is None:
            result.issues.append(
                ParseIssue(b_i + 1, "Block has no '-->' timing line; skipped.")
            )
            continue
        left, right = (part.strip() for part in TIMING_LINE_RE.split(lines[timing_idx])[:2])
        start = parse_timestamp(left)
        end = parse_timestamp(right.split()[0] if right else "")
        if start is None:
            result.issues.append(
                ParseIssue(b_i + 1, f"Malformed start timestamp '{left}'; block skipped.")
            )
            continue
        if end is None:
            result.issues.append(
                ParseIssue(b_i + 1, f"Malformed end timestamp '{right}'; treated as open-ended.")
            )
        text_lines = lines[timing_idx + 1 :]
        text = "\n".join(ln for ln in text_lines if ln.strip())
        raw.append((start, end, text, None))
    if not raw and not result.issues:
        result.issues.append(ParseIssue(1, "No subtitle blocks found."))
    result.segments = _format_segments(raw, result.issues, "srt", duration)
    return result


# ---------------------------------------------------------------------------
# VTT
# ---------------------------------------------------------------------------

def parse_vtt(content: str, duration: float | None = None) -> ParseResult:
    result = ParseResult(format="vtt")
    if content.startswith("﻿"):
        content = content[1:]
    if "\r\n" in content:
        content = content.replace("\r\n", "\n")
    if not content.lstrip().startswith("WEBVTT"):
        result.issues.append(ParseIssue(1, "Missing WEBVTT header; parsing anyway."))
    body = content
    # drop the header line
    body = re.sub(r"^WEBVTT[^\n]*\n", "", body.lstrip())
    blocks = re.split(r"\n\s*\n", body.strip())
    raw: list[tuple[float | None, float | None, str, str | None]] = []
    for b_i, block in enumerate(blocks):
        lines = block.split("\n")
        if not any(ln.strip() for ln in lines):
            continue
        first = lines[0].strip()
        if first.startswith(("NOTE", "STYLE", "REGION")):
            continue
        timing_idx = next(
            (i for i, ln in enumerate(lines) if TIMING_LINE_RE.search(ln)), None
        )
        if timing_idx is None:
            result.issues.append(
                ParseIssue(b_i + 1, "Block has no cue timing; skipped.")
            )
            continue
        left, right = (part.strip() for part in TIMING_LINE_RE.split(lines[timing_idx])[:2])
        start = parse_timestamp(left)
        right_first = right.split()[0] if right else ""
        end = parse_timestamp(right_first)
        if start is None:
            result.issues.append(
                ParseIssue(b_i + 1, f"Malformed cue start '{left}'; block skipped.")
            )
            continue
        if end is None:
            result.issues.append(
                ParseIssue(b_i + 1, f"Malformed cue end '{right_first}'; treated as open-ended.")
            )
        text = "\n".join(ln for ln in lines[timing_idx + 1 :] if ln.strip())
        raw.append((start, end, text, None))
    result.segments = _format_segments(raw, result.issues, "vtt", duration)
    return result


# ---------------------------------------------------------------------------
# plain-text classroom transcripts (docx / pdf / txt)
# ---------------------------------------------------------------------------

def _docx_paragraphs(path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(path) as zf:
            xml_bytes = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise SubtitleParseError("The .docx file is corrupt or missing its document body.") from exc
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise SubtitleParseError("The .docx file contains invalid XML.") from exc
    paragraphs: list[str] = []
    for p in root.iter(f"{WORD_NS}p"):
        parts = [t.text or "" for t in p.iter(f"{WORD_NS}t")]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _pdf_lines(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise SubtitleParseError("PDF support requires the 'pypdf' package.") from exc
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise SubtitleParseError("Could not open the PDF file.") from exc
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for ln in text.splitlines():
            stripped = ln.strip()
            if stripped:
                lines.append(stripped)
    return lines


def _txt_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover
        text = raw.decode("utf-8", errors="replace")
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def parse_transcript_lines(
    lines: list[str],
    fmt: str,
    duration: float | None = None,
    source_name: str = "transcript",
) -> ParseResult:
    """Segment a classroom transcript whose paragraphs are timestamp-delimited."""
    result = ParseResult(format=fmt)
    raw: list[tuple[float | None, float | None, str, str | None]] = []
    current_start: float | None = None
    current_lines: list[str] = []
    current_speaker: str | None = None
    seen_speaker: str | None = None
    preamble: list[str] = []

    def flush() -> None:
        nonlocal current_start, current_lines, current_speaker
        text = " ".join(current_lines)
        if current_start is None:
            if text.strip():
                preamble.append(text.strip())
            current_lines = []
            return
        raw.append((current_start, None, text, current_speaker))
        current_start = None
        current_lines = []
        current_speaker = None

    for ln in lines:
        m = PLAIN_TS_RE.match(ln)
        if m:
            ts = parse_timestamp(m.group(1))
            if ts is None:
                result.issues.append(
                    ParseIssue(len(result.issues) + 1, f"Malformed timestamp '{ln}'; line ignored.")
                )
                continue
            flush()
            current_start = ts
            continue
        sm = SPEAKER_RE.match(ln)
        if sm:
            seen_speaker = " ".join(ln.split())
            if current_start is not None and not current_lines:
                current_speaker = seen_speaker
            continue
        if current_start is None:
            # text before the first timestamp
            if not raw:
                preamble.append(ln)
            continue
        if not current_lines and seen_speaker and seen_speaker not in ln:
            current_speaker = current_speaker or seen_speaker
        current_lines.append(ln)
    flush()

    if preamble and not raw:
        # No timestamps at all — synchronized playback would be impossible.
        raise SubtitleParseError(
            f"No timestamps found in {source_name}. "
            "Add timestamps like '0:08' before each passage, or upload an .srt / .vtt file."
        )
    if not raw:
        raise SubtitleParseError(
            f"Could not find any readable content in {source_name}."
        )
    if preamble:
        # Text before the first timestamp becomes a leading segment at t=0.
        raw.insert(0, (0.0, None, " ".join(preamble), None))
    starts = [s for s, _, _, _ in raw if s is not None]
    if starts and any(b < a for a, b in zip(starts, starts[1:])):
        result.issues.append(
            ParseIssue(0, "Some timestamps are out of order; later values were kept.")
        )
    result.segments = _format_segments(raw, result.issues, fmt, duration)
    return result


def parse_transcript_file(path: Path, duration: float | None = None) -> ParseResult:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return parse_transcript_lines(_docx_paragraphs(path), "transcript-docx", duration, path.name)
    if suffix == ".pdf":
        return parse_transcript_lines(_pdf_lines(path), "transcript-pdf", duration, path.name)
    if suffix == ".txt":
        return parse_transcript_lines(_txt_lines(path), "transcript-txt", duration, path.name)
    raise SubtitleParseError(f"Unsupported transcript format: {suffix or path.name}")


# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------

def parse_subtitle_file(path: Path, duration: float | None = None) -> ParseResult:
    """Parse any supported subtitle/transcript file by extension."""
    if not path.exists():
        raise SubtitleParseError(f"Subtitle file not found: {path.name}")
    suffix = path.suffix.lower()
    if suffix in {".docx", ".pdf", ".txt"}:
        return parse_transcript_file(path, duration)
    if suffix == ".srt":
        text = _read_text(path)
        return parse_srt(text, duration)
    if suffix == ".vtt":
        text = _read_text(path)
        return parse_vtt(text, duration)
    raise SubtitleParseError(
        f"Unsupported subtitle format '{suffix}'. Use .srt, .vtt, .txt, .docx or .pdf."
    )


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")  # pragma: no cover

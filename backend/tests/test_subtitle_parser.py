"""Tests for SRT / VTT / transcript parsing."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.subtitle_parser import (  # noqa: E402
    SubtitleParseError,
    parse_srt,
    parse_subtitle_file,
    parse_timestamp,
    parse_transcript_lines,
    parse_vtt,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# timestamps
# ---------------------------------------------------------------------------

class TestParseTimestamp:
    def test_srt_style(self):
        assert parse_timestamp("00:00:12,500") == pytest.approx(12.5)

    def test_vtt_style(self):
        assert parse_timestamp("00:12.500") == pytest.approx(12.5)

    def test_plain_transcript(self):
        assert parse_timestamp("1:02:33") == pytest.approx(3753.0)
        assert parse_timestamp("45:51") == pytest.approx(45 * 60 + 51)

    def test_malformed(self):
        assert parse_timestamp("not-a-time") is None
        assert parse_timestamp("") is None
        assert parse_timestamp("99:99") is None
        assert parse_timestamp("abc:def,123") is None


# ---------------------------------------------------------------------------
# SRT
# ---------------------------------------------------------------------------

SRT_SAMPLE = """1
00:00:12,500 --> 00:00:16,200
Artificial intelligence is changing the way
software is developed.

2
00:00:16,200 --> 00:00:20,000
We deployed the application yesterday.

3
00:01:05,000 --> 00:01:09,750
Machine learning models need data.
"""


class TestSrt:
    def test_normal_srt(self):
        result = parse_srt(SRT_SAMPLE)
        assert result.format == "srt"
        assert len(result.segments) == 3
        seg = result.segments[0]
        assert seg["startTime"] == pytest.approx(12.5)
        assert seg["endTime"] == pytest.approx(16.2)
        assert "Artificial intelligence" in seg["text"]
        assert "\n" not in seg["text"]  # normalized whitespace

    def test_explicit_end_times_kept(self):
        result = parse_srt(SRT_SAMPLE)
        # segment 1 ends where segment 2 starts; explicit end times are kept
        assert result.segments[0]["endTime"] == pytest.approx(16.2)
        assert result.segments[1]["endTime"] == pytest.approx(20.0)
        assert result.segments[2]["endTime"] == pytest.approx(69.75)

    def test_malformed_timestamp_skips_block(self):
        bad = """1
00:00:12,500 --> 00:00:16,200
Fine line.

2
garbage --> also-garbage
Broken block.

3
00:00:20,000 --> 00:00:22,000
Still fine.
"""
        result = parse_srt(bad)
        assert len(result.segments) == 2
        assert any("Malformed start" in i.message for i in result.issues)

    def test_missing_timing_line(self):
        result = parse_srt("just some text\nwithout timing")
        assert result.segments == []
        assert len(result.issues) >= 1

    def test_crlf_and_bom(self):
        content = "﻿" + SRT_SAMPLE.replace("\n", "\r\n")
        result = parse_srt(content)
        assert len(result.segments) == 3

    def test_multiple_segments_ordered(self):
        result = parse_srt(SRT_SAMPLE)
        starts = [s["startTime"] for s in result.segments]
        assert starts == sorted(starts)


# ---------------------------------------------------------------------------
# VTT
# ---------------------------------------------------------------------------

VTT_SAMPLE = """WEBVTT

00:00:12.500 --> 00:00:16.200
Artificial intelligence is changing the way.

NOTE this is a comment
that spans two lines

intro-cue
00:00:16.200 --> 00:00:20.000 align:start position:10%
We deployed the application yesterday.
"""


class TestVtt:
    def test_normal_vtt(self):
        result = parse_vtt(VTT_SAMPLE)
        assert result.format == "vtt"
        assert len(result.segments) == 2
        assert result.segments[0]["startTime"] == pytest.approx(12.5)
        assert "deployed" in result.segments[1]["text"]

    def test_note_blocks_ignored(self):
        result = parse_vtt(VTT_SAMPLE)
        assert all("comment" not in s["text"] for s in result.segments)

    def test_cue_identifier_ignored(self):
        result = parse_vtt(VTT_SAMPLE)
        assert "intro-cue" not in result.segments[1]["text"]

    def test_cue_settings_ignored(self):
        result = parse_vtt(VTT_SAMPLE)
        assert "align:start" not in result.segments[1]["text"]

    def test_malformed_vtt_cue(self):
        vtt = "WEBVTT\n\nbroken --> times\nText only.\n"
        result = parse_vtt(vtt)
        assert result.segments == []
        assert result.issues


# ---------------------------------------------------------------------------
# classroom transcript (timestamp-per-paragraph style)
# ---------------------------------------------------------------------------

TRANSCRIPT_LINES = [
    "From Gimlet, this is reply All.",
    "I'm Alex Goldman.",
    "0:08",
    "Speaker 2",
    "And PJ.",
    "0:13",
    "Speaker 1",
    "So about seven months ago I got a phone call.",
    "0:28",
    "And I don't know what it is about 1800 numbers.",
]


class TestTranscript:
    def test_segmentation(self):
        result = parse_transcript_lines(TRANSCRIPT_LINES, "transcript-txt", duration=600)
        # preamble becomes a leading segment at t=0
        assert len(result.segments) == 4
        assert result.segments[0]["startTime"] == 0.0
        assert "reply All" in result.segments[0]["text"]
        assert result.segments[1]["startTime"] == pytest.approx(8.0)
        assert result.segments[1]["speaker"] == "Speaker 2"
        assert result.segments[2]["speaker"] == "Speaker 1"

    def test_end_times_chain(self):
        result = parse_transcript_lines(TRANSCRIPT_LINES, "transcript-txt", duration=600)
        assert result.segments[1]["endTime"] == pytest.approx(13.0)
        assert result.segments[-1]["endTime"] == pytest.approx(600.0)

    def test_speaker_lines_not_in_text(self):
        result = parse_transcript_lines(TRANSCRIPT_LINES, "transcript-txt", duration=600)
        assert all("Speaker" not in s["text"] for s in result.segments)

    def test_no_timestamps_raises(self):
        lines = ["First sentence here.", "Second sentence here."]
        with pytest.raises(SubtitleParseError, match="No timestamps"):
            parse_transcript_lines(lines, "transcript-txt", duration=120)

    def test_empty_raises(self):
        with pytest.raises(SubtitleParseError):
            parse_transcript_lines([], "transcript-txt")

    def test_duplicate_timestamps_get_minimum_duration(self):
        lines = ["0:24", "First", "0:24", "Second", "1:00", "Third"]
        result = parse_transcript_lines(lines, "transcript-txt", duration=300)
        assert result.segments[0]["endTime"] >= result.segments[0]["startTime"] + 0.3


# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------

class TestDispatcher:
    def test_unsupported_extension(self):
        with pytest.raises(SubtitleParseError):
            parse_subtitle_file(Path("episode.xyz"))


# ---------------------------------------------------------------------------
# real dataset files
# ---------------------------------------------------------------------------

class TestRealTranscripts:
    def test_docx_transcript_102(self):
        path = PROJECT_ROOT / "datasets" / "102_ReplyAll_LongDistance_Pt1_Transcript.docx"
        result = parse_subtitle_file(path, duration=2789.1)
        assert result.format == "transcript-docx"
        assert len(result.segments) > 300
        assert all(s["endTime"] > s["startTime"] for s in result.segments)
        starts = [s["startTime"] for s in result.segments]
        assert starts[0] == 0.0
        assert starts[-1] < 2789.1
        assert any("cloud" in s["text"].lower() for s in result.segments)

    def test_pdf_transcript_103(self):
        path = PROJECT_ROOT / "datasets" / "103_ReplyAll_LongDistance_Pt2_Transcript.pdf"
        result = parse_subtitle_file(path, duration=2606.6)
        assert result.format == "transcript-pdf"
        assert len(result.segments) > 300
        assert all(s["endTime"] > s["startTime"] for s in result.segments)
        assert any("Delhi" in s["text"] for s in result.segments)

    def test_pdf_transcript_164(self):
        path = PROJECT_ROOT / "datasets" / "164_ReplyAll_LongDistance_TheRealAlexMartin_Transcript.pdf"
        result = parse_subtitle_file(path, duration=1779.7)
        assert result.format == "transcript-pdf"
        assert len(result.segments) > 150
        assert all(s["endTime"] > s["startTime"] for s in result.segments)
        assert result.segments[-1]["startTime"] < 1779.7

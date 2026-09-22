"""Tests for the Excel vocabulary importer."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.excel_parser import (  # noqa: E402
    CANONICAL_FIELDS,
    ExcelParseError,
    auto_mapping,
    import_vocabulary_excel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

XLSX_102 = PROJECT_ROOT / "datasets" / "102_ReplyAll_LongDistance_Pt1_Vocab.xlsx"
XLSX_103 = PROJECT_ROOT / "datasets" / "103_ReplyAll_LongDistance_Pt2_Vocab.xlsx"
XLSX_164 = PROJECT_ROOT / "datasets" / "164_ReplyAll_LongDistance_TheRealAlexMartin_Vocab.xlsx"


# ---------------------------------------------------------------------------
# auto column mapping
# ---------------------------------------------------------------------------

class TestAutoMapping:
    def test_real_headers_from_source_files(self):
        headers = ["Word / Expression", "Base Form", "Meaning (Persian)",
                   "Meaning (English)", "POS", "Notes", "Example"]
        mapping = auto_mapping(headers)
        assert mapping == {
            "word": 0,
            "baseForm": 1,
            "persianMeaning": 2,
            "englishMeaning": 3,
            "partOfSpeech": 4,
            "notes": 5,
            "example": 6,
        }

    def test_alternative_headers(self):
        headers = ["Term", "Lemma", "Persian", "Definition", "Part of Speech", "Hint", "Sample"]
        mapping = auto_mapping(headers)
        assert mapping["word"] == 0
        assert mapping["baseForm"] == 1
        assert mapping["persianMeaning"] == 2
        assert mapping["englishMeaning"] == 3
        assert mapping["partOfSpeech"] == 4

    def test_unknown_headers_left_none(self):
        mapping = auto_mapping(["Column A", "Column B"])
        assert mapping["word"] is None


# ---------------------------------------------------------------------------
# synthetic workbooks
# ---------------------------------------------------------------------------

def _write_workbook(path: Path, rows: list[list], headers: list[str]) -> Path:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


class TestSyntheticWorkbook:
    def test_valid_workbook(self, tmp_path):
        path = _write_workbook(
            tmp_path / "ok.xlsx",
            [
                ["deploy", "deploy", "مستقر کردن", "to put into production", "verb", "SE term", "We deployed it."],
                ["runway", "run runway", "باند فرودگاه", "a strip for takeoff", "noun", "", "The runway was long."],
            ],
            ["Word", "Base Form", "Persian", "English", "POS", "Notes", "Example"],
        )
        result = import_vocabulary_excel(path)
        assert result.report.imported == 2
        assert result.entries[0].word == "deploy"
        assert result.entries[0].persian_meaning == "مستقر کردن"
        assert result.entries[1].part_of_speech == "noun"

    def test_missing_word_column_raises(self, tmp_path):
        path = _write_workbook(
            tmp_path / "bad.xlsx",
            [["a", "b"]],
            ["Random", "Stuff"],
        )
        with pytest.raises(ExcelParseError, match="word column"):
            import_vocabulary_excel(path)

    def test_duplicate_entries_reported(self, tmp_path):
        path = _write_workbook(
            tmp_path / "dups.xlsx",
            [
                ["deploy", "deploy", "x", "y", "verb", "", ""],
                ["Deploy", "deploy", "x2", "y2", "verb", "", ""],  # case dup
                ["run", "run", "x3", "y3", "verb", "", ""],
            ],
            ["Word", "Base", "Persian", "English", "POS", "Notes", "Example"],
        )
        result = import_vocabulary_excel(path)
        assert result.report.imported == 2
        assert len(result.report.duplicates) == 1
        assert result.report.duplicates[0]["word"] == "Deploy"
        assert any("duplicate" in w for w in result.report.warnings)

    def test_empty_rows_skipped(self, tmp_path):
        path = _write_workbook(
            tmp_path / "empty.xlsx",
            [
                ["deploy", "deploy", "x", "y", "verb", "", ""],
                [None, None, None, None, None, None, None],
                ["", "", "", "", "", "", ""],
                ["run", "run", "a", "b", "verb", "", ""],
            ],
            ["Word", "Base", "Persian", "English", "POS", "Notes", "Example"],
        )
        result = import_vocabulary_excel(path)
        assert result.report.imported == 2
        assert result.report.skipped_empty == 2

    def test_rows_without_word_skipped(self, tmp_path):
        path = _write_workbook(
            tmp_path / "noword.xlsx",
            [
                ["deploy", "deploy", "x", "y", "verb", "", ""],
                [None, "base only", "p", "e", "noun", "", ""],
            ],
            ["Word", "Base", "Persian", "English", "POS", "Notes", "Example"],
        )
        result = import_vocabulary_excel(path)
        assert result.report.imported == 1
        assert result.report.skipped_missing_word == 1

    def test_fully_empty_workbook_raises(self, tmp_path):
        path = _write_workbook(tmp_path / "empty2.xlsx", [], ["Word", "Base"])
        with pytest.raises(ExcelParseError):
            import_vocabulary_excel(path)

    def test_custom_mapping_overrides(self, tmp_path):
        path = _write_workbook(
            tmp_path / "mapped.xlsx",
            [["deploy", "به فارسی", "in english"]],
            ["Kolon1", "Kolon2", "Kolon3"],
        )
        result = import_vocabulary_excel(
            path,
            {"word": 0, "persianMeaning": 1, "englishMeaning": 2},
        )
        assert result.entries[0].word == "deploy"
        assert result.entries[0].persian_meaning == "به فارسی"
        assert result.entries[0].english_meaning == "in english"

    def test_unsupported_extension(self, tmp_path):
        path = tmp_path / "old.xls"
        path.write_bytes(b"not a real excel file")
        with pytest.raises(ExcelParseError, match="Unsupported"):
            import_vocabulary_excel(path)


# ---------------------------------------------------------------------------
# the three real vocabulary workbooks
# ---------------------------------------------------------------------------

class TestRealVocabularyFiles:
    @pytest.mark.parametrize(
        "path,min_count",
        [
            (XLSX_102, 60),
            (XLSX_103, 40),
            (XLSX_164, 40),
        ],
    )
    def test_parses_real_files(self, path: Path, min_count: int):
        assert path.exists(), f"missing source file: {path}"
        result = import_vocabulary_excel(path)
        assert result.report.imported >= min_count
        assert set(result.mapping.keys()) == set(CANONICAL_FIELDS)
        # all real headers map to real columns
        assert all(result.mapping[f] is not None for f in CANONICAL_FIELDS)
        # every entry has a word
        assert all(e.word for e in result.entries)
        # at least some entries carry Persian + English meanings
        with_fa = sum(1 for e in result.entries if e.persian_meaning)
        with_en = sum(1 for e in result.entries if e.english_meaning)
        assert with_fa > min_count * 0.8
        assert with_en > min_count * 0.8

    def test_102_contains_known_words(self):
        result = import_vocabulary_excel(XLSX_102)
        words = {e.word.casefold() for e in result.entries}
        assert "investigate" in words
        assert "stake out" in words

    def test_164_contains_known_words(self):
        result = import_vocabulary_excel(XLSX_164)
        words = {e.word.casefold() for e in result.entries}
        assert "compromised" in words
        assert "spoiler" in words

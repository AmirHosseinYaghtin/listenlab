"""Vocabulary Excel importer with flexible column mapping.

The three source workbooks happen to share the same headers, but the importer
does not rely on that: headers are auto-mapped through a synonym table and the
UI can override any mapping before confirming an import.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CANONICAL_FIELDS = [
    "word",
    "baseForm",
    "persianMeaning",
    "englishMeaning",
    "partOfSpeech",
    "notes",
    "example",
]

REQUIRED_FIELDS = ["word"]

# normalized header (lowercase, alphanumeric only, Persian preserved) -> field
_HEADER_SYNONYMS: dict[str, str] = {}
def _norm_header(value: str) -> str:
    return re.sub(r"[^0-9a-z\u0600-\u06ff]+", "", str(value).casefold())


def _register(field_name: str, *aliases: str) -> None:
    for alias in aliases:
        _HEADER_SYNONYMS[_norm_header(alias)] = field_name


_register("word", "word", "words", "word expression", "word/expression", "expression",
          "term", "phrase", "vocabulary", "vocab", "keyword", "headword",
          "کلمه", "واژه", "عبارت", "کلمه / عبارت", "واژگان")
_register("baseForm", "base form", "base", "lemma", "root", "baseform", "stem",
          "ریشه", "ریشه کلمه", "ف form پایه")
_register("persianMeaning", "meaning (persian)", "persian meaning", "persian", "farsi",
          "meaning persian", "translation (persian)", "persian translation",
          "ترجمه فارسی", "معنی فارسی", "فارسی", "ترجمه", "معنی")
_register("englishMeaning", "meaning (english)", "english meaning", "english", "meaning",
          "definition", "translation (english)", "english translation", "gloss",
          "ترجمه انگلیسی", "معنی انگلیسی", "انگلیسی", "تعریف")
_register("partOfSpeech", "pos", "part of speech", "partofspeech", "word class", "type",
          "grammatical class", "کلاس دستوری", "نوع", "نوع کلمه")
_register("notes", "notes", "note", "explanation", "explanation / notes", "remarks",
          "comment", "comments", "hint", "tips", "توضیح", "توضیحات", "یادداشت")
_register("example", "example", "examples", "example sentence", "sample", "sentence",
          "usage", "example sentence(s)", "جمله", "مثال", "جمله نمونه", "نمونه جمله")


class ExcelParseError(Exception):
    """Raised when the workbook cannot be imported."""


@dataclass
class VocabularyEntry:
    word: str
    base_form: str | None = None
    persian_meaning: str | None = None
    english_meaning: str | None = None
    part_of_speech: str | None = None
    notes: str | None = None
    example: str | None = None
    row_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "word": self.word,
            "baseForm": self.base_form,
            "persianMeaning": self.persian_meaning,
            "englishMeaning": self.english_meaning,
            "partOfSpeech": self.part_of_speech,
            "notes": self.notes,
            "example": self.example,
            "rowNumber": self.row_number,
        }


@dataclass
class ExcelImportReport:
    total_rows: int = 0
    imported: int = 0
    skipped_empty: int = 0
    skipped_missing_word: int = 0
    duplicates: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExcelImportResult:
    headers: list[str]
    mapping: dict[str, int | None]          # canonical field -> column index
    entries: list[VocabularyEntry]
    report: ExcelImportReport
    sheet_name: str

    def preview_dict(self, limit: int = 12) -> dict[str, Any]:
        return {
            "headers": self.headers,
            "mapping": self.mapping,
            "sheetName": self.sheet_name,
            "previewEntries": [e.to_dict() for e in self.entries[:limit]],
            "entryCount": len(self.entries),
            "report": {
                "totalRows": self.report.total_rows,
                "imported": self.report.imported,
                "skippedEmpty": self.report.skipped_empty,
                "skippedMissingWord": self.report.skipped_missing_word,
                "duplicates": self.report.duplicates,
                "warnings": self.report.warnings,
            },
        }


def _cell_to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def auto_mapping(headers: list[str]) -> dict[str, int | None]:
    mapping: dict[str, int | None] = {f: None for f in CANONICAL_FIELDS}
    for idx, header in enumerate(headers):
        if not header:
            continue
        key = _norm_header(header)
        field_name = _HEADER_SYNONYMS.get(key)
        if field_name is None:
            # loose contains-match, e.g. "Meaning (Persian) " variants
            for alias, f in _HEADER_SYNONYMS.items():
                if alias and (alias in key or key in alias) and len(alias) >= 4:
                    field_name = f
                    break
        if field_name and mapping[field_name] is None:
            mapping[field_name] = idx
    return mapping


def _load_rows(path: Path) -> tuple[list[str], list[list[Any]], str]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover
        raise ExcelParseError("Excel support requires the 'openpyxl' package.") from exc
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        raise ExcelParseError(
            f"Unsupported spreadsheet format '{path.suffix}'. Please save the file as .xlsx."
        )
    try:
        wb = load_workbook(str(path), read_only=True, data_only=True)
    except Exception as exc:
        raise ExcelParseError(
            "Could not open the spreadsheet. Make sure it is a valid .xlsx file."
        ) from exc
    try:
        # choose the sheet with the most rows (first sheet by default)
        best_ws, best_size = None, -1
        for ws in wb.worksheets:
            size = (ws.max_row or 0) * (ws.max_column or 0)
            if size > best_size:
                best_ws, best_size = ws, size
        if best_ws is None:
            raise ExcelParseError("The spreadsheet has no worksheets.")
        rows_iter = best_ws.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            raise ExcelParseError("The spreadsheet is empty.") from None
        headers = [_cell_to_str(h) for h in header_row]
        # trim trailing empty header cells
        while headers and not headers[-1]:
            headers.pop()
        if not headers:
            raise ExcelParseError("The spreadsheet has no header row.")
        data_rows: list[list[Any]] = []
        width = len(headers)
        for row in rows_iter:
            values = list(row[:width]) + [None] * max(0, width - len(row))
            data_rows.append(values)
        return headers, data_rows, best_ws.title
    finally:
        wb.close()


def import_vocabulary_excel(
    path: Path, mapping: dict[str, int | None] | None = None
) -> ExcelImportResult:
    """Parse an Excel vocabulary file into entries + a human-readable report."""
    headers, data_rows, sheet_name = _load_rows(path)
    resolved = dict(mapping) if mapping else auto_mapping(headers)

    if resolved.get("word") is None:
        raise ExcelParseError(
            "Could not find a word column. Detected headers: "
            + ", ".join(h or "(empty)" for h in headers)
            + ". Please map a column to 'Word / Expression' before importing."
        )

    report = ExcelImportReport()
    entries: list[VocabularyEntry] = []
    seen: dict[str, int] = {}

    for i, row in enumerate(data_rows):
        row_number = i + 2  # 1-based + header row
        values = [_cell_to_str(v) for v in row]
        if not any(values):
            report.skipped_empty += 1
            continue
        report.total_rows += 1

        def get(field_name: str) -> str | None:
            col = resolved.get(field_name)
            if col is None or col >= len(values):
                return None
            val = values[col].strip()
            return val or None

        word = get("word")
        if not word:
            report.skipped_missing_word += 1
            continue

        key = re.sub(r"\s+", " ", word).casefold()
        if key in seen:
            report.duplicates.append(
                {"word": word, "firstRow": seen[key], "duplicateRow": row_number}
            )
            continue
        seen[key] = row_number

        base = get("baseForm")
        entries.append(
            VocabularyEntry(
                word=word,
                base_form=base,
                persian_meaning=get("persianMeaning"),
                english_meaning=get("englishMeaning"),
                part_of_speech=get("partOfSpeech"),
                notes=get("notes"),
                example=get("example"),
                row_number=row_number,
            )
        )

    report.imported = len(entries)
    if report.duplicates:
        report.warnings.append(
            f"{len(report.duplicates)} duplicate entr{'y' if len(report.duplicates) == 1 else 'ies'} "
            "were skipped (first occurrence kept)."
        )
    if report.skipped_missing_word:
        report.warnings.append(
            f"{report.skipped_missing_word} row(s) had no word and were skipped."
        )
    if not entries:
        raise ExcelParseError(
            "No vocabulary entries were found in this spreadsheet "
            "(the file may be empty or the word column mapping may be wrong)."
        )

    return ExcelImportResult(
        headers=headers,
        mapping=resolved,
        entries=entries,
        report=report,
        sheet_name=sheet_name,
    )

"""Vocabulary matcher.

Pipeline (UI-independent, per the architecture requirement):

    SubtitleSegment[]  +  VocabularyEntry[]
                ↓
    AnnotatedSubtitleSegment[]   (text split into parts, each part optionally
                                  bound to a vocabulary entry)

Matching strategy:
  * case-insensitive
  * whole-word matching via boundaries that never match inside larger words
    ("AI" never fires inside "chair" / "said")
  * multi-word phrases with flexible whitespace
  * common English inflections for each content word (plural, -ed, -ing,
    -es, consonant doubling, e-drop) using a small, extensible ruleset
  * longest expression wins when candidates overlap
"""
from __future__ import annotations

import re
from typing import Any, Iterable

# Function words that should never be "inflected" inside a phrase pattern.
_CLOSED_CLASS = {
    "a", "an", "the", "of", "on", "in", "at", "to", "for", "or", "and", "as",
    "by", "from", "with", "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "this", "that", "these", "those", "you", "your", "we", "our",
    "they", "their", "them", "he", "she", "his", "her", "my", "me", "us", "i",
    "do", "does", "did", "not", "no", "so", "but", "if", "than", "then",
    "there", "here", "up", "down", "out", "off", "over", "under", "about",
    "into", "via", "per", "also", "just", "very", "much", "more", "most",
}

_VOWELS = set("aeiou")


def inflection_forms(word: str) -> list[str]:
    """Generate common surface forms of a single English word."""
    w = word.casefold()
    forms = {w}
    if w in _CLOSED_CLASS or not w.isalpha() or len(w) < 2:
        return [w]

    # plural / 3rd person singular
    if w.endswith(("s", "x", "z", "ch", "sh")):
        forms.add(w + "es")
    elif w.endswith("y") and len(w) > 1 and w[-2] not in _VOWELS:
        forms.add(w[:-1] + "ies")
    else:
        forms.add(w + "s")

    # past / gerund
    if w.endswith("e"):
        forms.add(w + "d")          # like -> liked, agree -> agreed
        if w.endswith(("ee", "oe", "ye")):
            forms.add(w + "ing")    # agree -> agreeing, see -> seeing
        else:
            forms.add(w[:-1] + "ed")    # write -> written-like "writed" still ok to offer
            forms.add(w[:-1] + "ing")   # make -> making
    else:
        forms.add(w + "ed")
        forms.add(w + "d")
        forms.add(w + "ing")
        # consonant doubling: stop -> stopped / stopping (short CVC stems)
        if (
            3 <= len(w) <= 5
            and w[-1] not in _VOWELS | {"w", "x", "y"}
            and w[-2] in _VOWELS
            and w[-3] not in _VOWELS
        ):
            forms.add(w + w[-1] + "ed")
            forms.add(w + w[-1] + "ing")

    if w.endswith("y") and len(w) > 1 and w[-2] not in _VOWELS:
        forms.add(w[:-1] + "ied")

    return sorted(forms)


def _alternation(word: str) -> str:
    forms = inflection_forms(word)
    if not forms:
        return re.escape(word)
    return "(?:" + "|".join(re.escape(f) for f in forms) + ")"


def expression_pattern(expression: str, base_form: str | None = None) -> str:
    """Build a regex fragment for a word/phrase (plus optional base form)."""
    expr = expression.strip()
    # strip wrapping punctuation but keep internal hyphens/apostrophes
    expr = expr.strip(".,;:!?\"'“”‘’()[]{}…")
    if not expr:
        return ""

    variants: list[str] = []
    for candidate in (expr, base_form.strip() if base_form else None):
        if not candidate:
            continue
        tokens = candidate.split()
        if not tokens:
            continue
        parts = [_alternation(tok) for tok in tokens]
        pattern = r"\s+".join(parts)
        if pattern not in variants:
            variants.append(pattern)
    if not variants:
        return re.escape(expr)
    if len(variants) == 1:
        return variants[0]
    return "(?:" + "|".join(variants) + ")"


# word characters that must not surround a match
_BOUNDARY = r"(?<![A-Za-z0-9_])"
_BOUNDARY_END = r"(?![A-Za-z0-9_])"


def compile_matcher(vocab: Iterable[dict]) -> tuple[re.Pattern | None, list[dict]]:
    """Compile all vocabulary expressions into one ordered regex.

    Returns (compiled_regex, ordered_entries). Longer expressions are placed
    first so they win at the same start position.
    """
    entries: list[dict] = []
    for i, v in enumerate(vocab):
        word = (v.get("word") or "").strip()
        if not word:
            continue
        entries.append(
            {
                "id": v.get("id") or str(v.get("rowNumber") or i),
                "word": word,
                "baseForm": v.get("baseForm"),
                "index": len(entries),
            }
        )
    if not entries:
        return None, []

    # longest expression first => longest-match-wins at each position
    ordered = sorted(entries, key=lambda e: len(e["word"]), reverse=True)
    alternatives = []
    for e in ordered:
        pat = expression_pattern(e["word"], e.get("baseForm"))
        if not pat:
            continue
        alternatives.append(f"(?P<v{e['index']}>{_BOUNDARY}{pat}{_BOUNDARY_END})")
    if not alternatives:
        return None, []
    regex = re.compile("|".join(alternatives), re.IGNORECASE)
    return regex, ordered


def annotate_text(
    text: str, regex: re.Pattern | None, entries: list[dict]
) -> list[dict[str, Any]]:
    """Split *text* into alternating plain/vocabulary parts.

    Returns [{"t": "...", "v": "vocabId"?}, ...]
    """
    if not text:
        return []
    if regex is None:
        return [{"t": text}]
    # group names are "v{original_index}" — map them back through the
    # original entry index, not the (sorted) list position.
    id_by_original_index = {e["index"]: e["id"] for e in entries}
    id_by_group: dict[int, str] = {}
    for name in regex.groupindex:
        try:
            gi = int(name[1:])
        except ValueError:  # pragma: no cover
            continue
        vocab_id = id_by_original_index.get(gi)
        if vocab_id is not None:
            id_by_group[regex.groupindex[name]] = vocab_id

    parts: list[dict[str, Any]] = []
    last = 0
    for m in regex.finditer(text):
        if m.start() < last:
            continue
        vocab_id = None
        for g_idx, value in m.groupdict().items():
            if value is not None:
                grp = regex.groupindex.get(g_idx)
                vocab_id = id_by_group.get(grp)
                break
        if vocab_id is None:
            continue
        if m.start() > last:
            parts.append({"t": text[last : m.start()]})
        parts.append({"t": m.group(0), "v": vocab_id})
        last = m.end()
    if last < len(text):
        parts.append({"t": text[last:]})
    if not parts:
        return [{"t": text}]
    return parts


def annotate_segments(
    segments: list[dict], vocab: list[dict]
) -> list[dict[str, Any]]:
    """Return segments enriched with vocabulary-annotated ``parts``."""
    regex, entries = compile_matcher(vocab)
    annotated = []
    for seg in segments:
        new_seg = dict(seg)
        new_seg["parts"] = annotate_text(seg.get("text", ""), regex, entries)
        annotated.append(new_seg)
    return annotated


def count_matches(segments: list[dict], vocab: list[dict]) -> dict[str, int]:
    """Count how many times each vocabulary expression appears in segments."""
    regex, entries = compile_matcher(vocab)
    counts: dict[str, int] = {}
    if regex is None:
        return counts
    word_by_id = {e["id"]: e["word"] for e in entries}
    for seg in segments:
        for part in annotate_text(seg.get("text", ""), regex, entries):
            vid = part.get("v")
            if vid:
                counts[vid] = counts.get(vid, 0) + 1
    return {word_by_id.get(k, k): v for k, v in counts.items()}

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
  * the Base Form column is honoured as an alternate surface form only when
    it has at least as many tokens as the expression, so a component word
    (base "will" of "sheer force of will") never matches standalone
  * all primary word patterns are attempted before any base-form alternate,
    so a dedicated entry always wins over another entry's base variant
    ("stereotype" beats the base variant of "stereotypically")
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


def _strip_expression(expression: str) -> str:
    """Trim whitespace and wrapping punctuation, keep internal hyphens."""
    return expression.strip().strip(".,;:!?\"'“”‘’()[]{}…")


def _token_pattern(expression: str) -> str | None:
    """Inflection-aware pattern for a whitespace-split expression."""
    tokens = expression.split()
    if not tokens:
        return None
    return r"\s+".join(_alternation(tok) for tok in tokens)


def _alternate_base_pattern(word: str, base_form: str | None) -> str | None:
    """Base Form as an alternate surface form of the same expression.

    Only kept when the base form has at least as many tokens as the
    expression: a component/headword base ("will" of "sheer force of will",
    "part" of "part on bad terms") must never become a standalone match.
    """
    if not base_form:
        return None
    expr = _strip_expression(word)
    base = _strip_expression(base_form)
    if not expr or not base or base.casefold() == expr.casefold():
        return None
    if len(base.split()) < len(expr.split()):
        return None
    expr_pat = _token_pattern(expr)
    base_pat = _token_pattern(base)
    if not base_pat or base_pat == expr_pat:
        return None
    return base_pat


def expression_pattern(expression: str, base_form: str | None = None) -> str:
    """Build a regex fragment for a word/phrase (plus optional base form)."""
    expr = _strip_expression(expression)
    if not expr:
        return ""
    expr_pat = _token_pattern(expr)
    if not expr_pat:
        return re.escape(expr)
    base_pat = _alternate_base_pattern(expr, base_form)
    if not base_pat:
        return expr_pat
    return f"(?:{expr_pat}|{base_pat})"


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
    primary_alternatives: list[str] = []
    base_alternatives: list[str] = []
    for e in ordered:
        expr = _strip_expression(e["word"])
        primary = _token_pattern(expr)
        if not primary:
            continue
        primary_alternatives.append(
            f"(?P<v{e['index']}>{_BOUNDARY}{primary}{_BOUNDARY_END})"
        )
        base_pat = _alternate_base_pattern(e["word"], e.get("baseForm"))
        if base_pat:
            base_alternatives.append(
                f"(?P<b{e['index']}>{_BOUNDARY}{base_pat}{_BOUNDARY_END})"
            )
    if not primary_alternatives:
        return None, []
    # Primaries first: a dedicated entry always wins over another entry's
    # base-form variant at the same position. Base alternates keep their own
    # longest-first order.
    base_alternatives.reverse()
    regex = re.compile("|".join(primary_alternatives + base_alternatives), re.IGNORECASE)
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

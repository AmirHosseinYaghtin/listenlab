"""Tests for the vocabulary matcher."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.vocab_matcher import (  # noqa: E402
    annotate_segments,
    annotate_text,
    compile_matcher,
    count_matches,
    expression_pattern,
    inflection_forms,
)


def vocab(*words: str) -> list[dict]:
    return [{"id": f"v{i}", "word": w, "baseForm": None} for i, w in enumerate(words)]


def matched_words(text: str, words: list[str]) -> list[str]:
    regex, entries = compile_matcher(vocab(*words))
    id_to_word = {e["id"]: e["word"] for e in entries}
    found = []
    for part in annotate_text(text, regex, entries):
        if part.get("v"):
            found.append(id_to_word[part["v"]])
    return found


# ---------------------------------------------------------------------------
# inflections
# ---------------------------------------------------------------------------

class TestInflections:
    def test_plurals(self):
        assert "models" in inflection_forms("model")
        assert "boxes" in inflection_forms("box")
        assert "cities" in inflection_forms("city")

    def test_past_tense(self):
        assert "deployed" in inflection_forms("deploy")
        assert "agreed" in inflection_forms("agree")
        assert "liked" in inflection_forms("like")

    def test_gerund(self):
        assert "deploying" in inflection_forms("deploy")
        assert "investigating" in inflection_forms("investigate")
        assert "agreeing" in inflection_forms("agree")

    def test_doubling(self):
        assert "stopped" in inflection_forms("stop")
        assert "stopping" in inflection_forms("stop")

    def test_closed_class_not_inflected(self):
        assert inflection_forms("on") == ["on"]


# ---------------------------------------------------------------------------
# exact / case / punctuation
# ---------------------------------------------------------------------------

class TestBasicMatching:
    def test_exact_match(self):
        assert matched_words("We use Docker every day.", ["docker"]) == ["docker"]

    def test_case_insensitive(self):
        assert matched_words("the AI system performed well", ["ai"]) == ["ai"]
        assert matched_words("Machine Learning is fun", ["machine learning"]) == ["machine learning"]

    def test_punctuation_around_word(self):
        assert matched_words("Deploy it now!", ["deploy"]) == ["deploy"]
        assert matched_words("(deploy)", ["deploy"]) == ["deploy"]

    def test_inflected_form_in_sentence(self):
        found = matched_words(
            "We deployed the application yesterday, and it is deploying more units.",
            ["deploy"],
        )
        assert found == ["deploy", "deploy"]

    def test_phrase_match(self):
        found = matched_words("It was a stake out for hours.", ["stake out"])
        assert found == ["stake out"]

    def test_phrase_inflected(self):
        found = matched_words("They staked out the building.", ["stake out"])
        assert found == ["stake out"]

    def test_base_form_matches_derived_entry(self):
        # entry word "legit" but base form "legitimate" also appears
        entries = [{"id": "v0", "word": "legit", "baseForm": "legitimate"}]
        regex, ordered = compile_matcher(entries)
        parts = annotate_text("The company seemed legitimate after all.", regex, ordered)
        assert any(p.get("v") == "v0" for p in parts)


# ---------------------------------------------------------------------------
# word boundaries — the critical correctness case
# ---------------------------------------------------------------------------

class TestWordBoundaries:
    def test_ai_does_not_match_inside_chair(self):
        assert matched_words("The chair is available.", ["ai"]) == []
        assert matched_words("He said nothing.", ["ai"]) == []

    def test_ai_matches_as_word(self):
        assert matched_words("The AI system performed well.", ["ai"]) == ["ai"]

    def test_no_partial_word_match(self):
        assert matched_words("Investigation is ongoing.", ["investigate"]) == []
        # but the inflected noun form of the same lemma is a different entry
        assert matched_words("We investigate everything.", ["investigate"]) == ["investigate"]

    def test_word_inside_word_not_matched(self):
        assert matched_words("Understanding is key.", ["under"]) == []
        assert matched_words("Tea time.", ["team"]) == []


# ---------------------------------------------------------------------------
# overlap resolution: longest wins
# ---------------------------------------------------------------------------

class TestLongestMatch:
    def test_phrase_wins_over_single_word(self):
        found = matched_words(
            "They did a stake out near the warehouse.",
            ["stake", "stake out"],
        )
        assert found == ["stake out"]

    def test_longer_expression_first(self):
        found = matched_words(
            "She showed sheer force of will.",
            ["will", "sheer force of will"],
        )
        assert found == ["sheer force of will"]


# ---------------------------------------------------------------------------
# parts rendering + segments
# ---------------------------------------------------------------------------

class TestAnnotate:
    def test_parts_recombine_to_original(self):
        text = "Artificial intelligence is changing software deployment."
        regex, entries = compile_matcher(vocab("software", "deployment"))
        parts = annotate_text(text, regex, entries)
        assert "".join(p["t"] for p in parts) == text
        flagged = [p for p in parts if p.get("v")]
        assert len(flagged) == 2

    def test_empty_vocab(self):
        regex, entries = compile_matcher([])
        assert regex is None
        assert annotate_text("anything", regex, entries) == [{"t": "anything"}]

    def test_annotate_segments(self):
        segments = [
            {"id": "0", "index": 0, "startTime": 0, "endTime": 1, "text": "We deployed it.", "speaker": None},
            {"id": "1", "index": 1, "startTime": 1, "endTime": 2, "text": "Nothing here.", "speaker": None},
        ]
        out = annotate_segments(segments, vocab("deploy"))
        assert any(p.get("v") == "v0" for p in out[0]["parts"])
        assert all(not p.get("v") for p in out[1]["parts"])
        # original fields preserved
        assert out[1]["text"] == "Nothing here."

    def test_count_matches(self):
        segments = [
            {"text": "deploy deploy Deployed"},
            {"text": "nothing"},
        ]
        counts = count_matches(segments, vocab("deploy"))
        assert counts == {"deploy": 3}


# ---------------------------------------------------------------------------
# expression pattern unit
# ---------------------------------------------------------------------------

class TestExpressionPattern:
    def test_pattern_is_valid_regex(self):
        import re
        pat = expression_pattern("machine learning")
        assert re.compile(pat, re.IGNORECASE)

    def test_strips_wrapping_punctuation(self):
        import re
        pat = expression_pattern('"deploy,"')
        assert re.fullmatch(pat, "deploy", re.IGNORECASE)

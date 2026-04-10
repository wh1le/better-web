"""Text quality heuristics: readability, slop detection, keyword stuffing."""
import re
import statistics
from collections import Counter

import textstat

from lib.settings import settings


def text_signals(text: str) -> tuple[int, list[str], dict]:
    """Score based on text content. Returns (points, flags, details)."""
    scoring = settings.scoring
    points = 0
    flags: list[str] = []
    details: dict[str, object] = {}

    words = text.split()
    word_count = len(words)
    sentences = [sent.strip() for sent in re.split(r'[.!?]+', text) if len(sent.strip()) > 5]

    # readability
    flesch = textstat.flesch_reading_ease(text)
    details["flesch_reading_ease"] = round(flesch, 1)
    details["grade_level"] = round(textstat.flesch_kincaid_grade(text), 1)
    if flesch < 10:
        points -= 5
        flags.append("very_hard_to_read")
    elif 30 <= flesch <= 70:
        points += 5

    # AI detection
    ai = ai_score(text)
    details["ai_score"] = round(ai, 2)
    if ai > 0.5:
        points += scoring.ai_penalty
        flags.append("likely_ai")

    # content length
    details["word_count"] = word_count
    if word_count < 100:
        points -= 25
        flags.append("thin")
    elif word_count < 200:
        points -= 10
        flags.append("short")
    elif word_count > 500:
        points += 5

    # keyword stuffing
    long_words = [w.lower() for w in words if len(w) > 4]
    if long_words:
        freq = Counter(long_words)
        top_word, top_count = freq.most_common(1)[0]
        ratio = top_count / len(long_words)
        if ratio > 0.05:
            points -= 10
            flags.append(f"keyword_stuffing:{top_word}")
            details["keyword_stuffing_ratio"] = round(ratio, 3)

    # repetitive bigrams
    if word_count > 20:
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        bigram_freq = Counter(bigrams)
        repeated = sum(1 for _, count in bigram_freq.items() if count > 3)
        repeat_ratio = repeated / max(len(bigrams), 1)
        if repeat_ratio > 0.05:
            points -= 10
            flags.append("repetitive")
            details["repetitive_bigram_ratio"] = round(repeat_ratio, 3)

    # sentence length variance
    if len(sentences) > 5:
        lengths = [len(sent.split()) for sent in sentences]
        mean = statistics.mean(lengths)
        if mean > 0:
            coefficient_of_variation = statistics.stdev(lengths) / mean
            details["sentence_variance"] = round(coefficient_of_variation, 2)
            if coefficient_of_variation < 0.3:
                points -= 5
                flags.append("uniform_sentences")

    # slop phrases
    text_lower = text.lower()
    slop_count = sum(1 for phrase in settings.lists.slop_phrases if phrase in text_lower)
    if slop_count >= 3:
        points -= 15
        flags.append(f"slop_phrases:{slop_count}")
    elif slop_count >= 1:
        points -= 3
    details["slop_phrase_count"] = slop_count

    # discussion signals
    discussion_count = sum(1 for marker in settings.lists.discussion_markers if marker in text_lower)
    if discussion_count >= 2:
        points += 10
        flags.append("discussion")

    return points, flags, details


# --- AI detection ---

try:
    from zippy.zippy import EnsembledZippy
    _zippy = EnsembledZippy()

    def ai_score(text: str) -> float:
        """Return 1.0 if AI-detected, 0.0 if human."""
        try:
            label, _conf = _zippy.run_on_text_chunked(text)
            return 1.0 if label == "AI" else 0.0
        except Exception:
            return 0.0
except ImportError:
    def ai_score(_text: str) -> float:  # type: ignore[misc]
        return 0.0

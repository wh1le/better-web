from unittest.mock import patch

from lib.text_scoring import text_signals


LONG_TEXT = "This is a sample article about technology. " * 80
SHORT_TEXT = "Short."


@patch("lib.text_scoring.settings")
@patch("lib.text_scoring.ai_score", return_value=0.0)
def test_long_text_gets_positive_score(mock_ai, mock_settings):
    mock_settings.scoring.ai_penalty = -20
    mock_settings.ai_phrases = []
    mock_settings.discussion_markers = []
    points, flags, details = text_signals(LONG_TEXT)
    assert details["word_count"] > 500


@patch("lib.text_scoring.settings")
@patch("lib.text_scoring.ai_score", return_value=0.0)
def test_short_text_gets_penalty(mock_ai, mock_settings):
    mock_settings.scoring.ai_penalty = -20
    mock_settings.ai_phrases = []
    mock_settings.discussion_markers = []
    points, flags, details = text_signals(SHORT_TEXT)
    assert "thin" in flags


@patch("lib.text_scoring.settings")
@patch("lib.text_scoring.ai_score", return_value=0.9)
def test_ai_detected_gets_penalty(mock_ai, mock_settings):
    mock_settings.scoring.ai_penalty = -20
    mock_settings.ai_phrases = []
    mock_settings.discussion_markers = []
    points, flags, _ = text_signals(LONG_TEXT)
    assert "likely_ai" in flags


@patch("lib.text_scoring.settings")
@patch("lib.text_scoring.ai_score", return_value=0.0)
def test_ai_phrases_detected(mock_ai, mock_settings):
    mock_settings.scoring.ai_penalty = -20
    mock_settings.ai_phrases = ["comprehensive guide", "dive into"]
    mock_settings.discussion_markers = []
    text = "This comprehensive guide will dive into the topic. Let's dive into it again. This comprehensive guide covers everything. " * 5
    points, flags, details = text_signals(text)
    assert details["slop_phrase_count"] >= 2


@patch("lib.text_scoring.settings")
@patch("lib.text_scoring.ai_score", return_value=0.0)
def test_discussion_markers_boost(mock_ai, mock_settings):
    mock_settings.scoring.ai_penalty = -20
    mock_settings.ai_phrases = []
    mock_settings.discussion_markers = ["replied", "upvote"]
    text = "User replied to the comment. Another user replied and got an upvote. " * 10
    points, flags, _ = text_signals(text)
    assert "discussion" in flags

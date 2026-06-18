from __future__ import annotations

from datetime import UTC, datetime

from crypto_radar.classifier import classify_article
from crypto_radar.models import Article, CategoryKeywords, KeywordsConfig, NegativeKeyword


def article(title: str, summary: str) -> Article:
    return Article(
        id="1",
        title=title,
        url="https://example.com/a",
        normalized_url="https://example.com/a",
        source_id="test",
        source_name="Test",
        source_type="rss",
        content_type="Paper",
        published_at=None,
        fetched_at=datetime(2026, 6, 18, tzinfo=UTC),
        summary=summary,
        fingerprint="fp",
    )


def keywords_config() -> KeywordsConfig:
    return KeywordsConfig(
        categories={
            "AEAD": CategoryKeywords(
                weight=4, keywords=["AEAD", "authenticated encryption", "認証暗号"]
            ),
            "Implementation": CategoryKeywords(weight=3, keywords=["constant-time", "実装"]),
        },
        negative_keywords=[NegativeKeyword(keyword="bitcoin", weight=-10)],
    )


def test_classifier_is_case_insensitive_for_english() -> None:
    result = classify_article(article("aead design", ""), keywords_config())
    assert "AEAD" in result.categories
    assert "AEAD" in result.title_keywords


def test_classifier_matches_japanese_keywords() -> None:
    result = classify_article(article("新しい認証暗号", "高速な実装"), keywords_config())
    assert result.categories == ["AEAD", "Implementation"]


def test_classifier_tracks_title_matches() -> None:
    result = classify_article(article("constant-time AEAD", ""), keywords_config())
    assert "constant-time" in result.title_keywords
    assert "AEAD" in result.title_keywords


def test_classifier_does_not_duplicate_same_keyword() -> None:
    result = classify_article(article("AEAD AEAD", "AEAD"), keywords_config())
    assert result.matched_keywords.count("AEAD") == 1


def test_classifier_tracks_negative_keyword() -> None:
    result = classify_article(article("Bitcoin price and AEAD", ""), keywords_config())
    assert "bitcoin" in result.negative_keywords

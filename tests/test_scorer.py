from __future__ import annotations

from datetime import UTC, datetime

from crypto_radar.classifier import classify_article
from crypto_radar.models import (
    Article,
    CategoryKeywords,
    KeywordsConfig,
    NegativeKeyword,
    ScoringConfig,
    SourceConfig,
)
from crypto_radar.scorer import above_notion_threshold, above_slack_threshold, score_article


def source(base_score: int = 2) -> SourceConfig:
    return SourceConfig(
        id="test",
        name="Test",
        type="rss",
        content_type="Paper",
        url="https://example.com/feed",
        base_score=base_score,
    )


def article(title: str, summary: str = "", published_at: datetime | None = None) -> Article:
    return Article(
        id="1",
        title=title,
        url="https://example.com/a",
        normalized_url="https://example.com/a",
        source_id="test",
        source_name="Test",
        source_type="rss",
        content_type="Paper",
        published_at=published_at,
        fetched_at=datetime(2026, 6, 18, tzinfo=UTC),
        summary=summary,
        fingerprint="fp",
    )


def keywords() -> KeywordsConfig:
    return KeywordsConfig(
        categories={
            "AEAD": CategoryKeywords(weight=4, keywords=["AEAD"]),
            "Implementation": CategoryKeywords(weight=3, keywords=["constant-time"]),
        },
        negative_keywords=[NegativeKeyword(keyword="bitcoin", weight=-10)],
    )


def test_base_score_is_applied() -> None:
    item = article("unrelated")
    result = score_article(
        item, source(7), classify_article(item, keywords()), keywords(), ScoringConfig()
    )
    assert result.score == 7


def test_title_multiplier_is_applied() -> None:
    item = article("AEAD")
    result = score_article(
        item, source(2), classify_article(item, keywords()), keywords(), ScoringConfig()
    )
    assert result.score == 10


def test_multiple_category_bonus_is_applied() -> None:
    item = article("AEAD constant-time")
    result = score_article(
        item, source(0), classify_article(item, keywords()), keywords(), ScoringConfig()
    )
    assert result.score == 16


def test_negative_score_is_applied() -> None:
    item = article("AEAD bitcoin")
    result = score_article(
        item, source(0), classify_article(item, keywords()), keywords(), ScoringConfig()
    )
    assert result.score == -2


def test_threshold_helpers() -> None:
    item = article("AEAD constant-time")
    result = score_article(
        item, source(0), classify_article(item, keywords()), keywords(), ScoringConfig()
    )
    item.score = result.score
    assert above_notion_threshold(item, ScoringConfig())
    assert above_slack_threshold(item, ScoringConfig())

from __future__ import annotations

from datetime import UTC, datetime

from crypto_radar.deduplicate import deduplicate_articles
from crypto_radar.models import Article
from crypto_radar.normalize import make_fingerprint
from crypto_radar.utils.urls import normalize_url


def article(url: str, title: str, source_id: str = "source") -> Article:
    normalized = normalize_url(url)
    return Article(
        id=title,
        title=title,
        url=url,
        normalized_url=normalized,
        source_id=source_id,
        source_name=source_id,
        source_type="rss",
        content_type="News",
        published_at=None,
        fetched_at=datetime(2026, 6, 18, tzinfo=UTC),
        fingerprint=make_fingerprint(source_id=source_id, normalized_url=normalized, title=title),
    )


def test_duplicate_same_url() -> None:
    first = article("https://example.com/a", "Title")
    second = article("https://example.com/a", "Title")
    unique, duplicates = deduplicate_articles([first, second])
    assert unique == [first]
    assert duplicates == [second]


def test_duplicate_tracking_parameter_only_differs() -> None:
    first = article("https://example.com/a?utm_source=x", "Title")
    second = article("https://example.com/a", "Title")
    unique, duplicates = deduplicate_articles([first, second])
    assert unique == [first]
    assert duplicates == [second]


def test_duplicate_same_title_and_url() -> None:
    first = article("https://example.com/a", "Same Title")
    second = article("https://example.com/a/", "Same Title")
    unique, duplicates = deduplicate_articles([first, second])
    assert unique == [first]
    assert duplicates == [second]


def test_duplicate_across_different_sources_with_same_url_and_title() -> None:
    first = article("https://example.com/a", "Title", source_id="a")
    second = article("https://example.com/a", "Title", source_id="b")
    unique, duplicates = deduplicate_articles([first, second])
    assert unique == [first]
    assert duplicates == [second]

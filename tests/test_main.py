from __future__ import annotations

from datetime import UTC, datetime

from crypto_radar.main import sort_articles_for_processing
from crypto_radar.models import Article


def article(title: str, source_id: str, published_at: datetime | None) -> Article:
    return Article(
        id=title,
        title=title,
        url=f"https://example.com/{title}",
        normalized_url=f"https://example.com/{title}",
        source_id=source_id,
        source_name=source_id,
        source_type="rss",
        content_type="News",
        published_at=published_at,
        fetched_at=datetime(2026, 6, 18, 0, 0, tzinfo=UTC),
        fingerprint=title,
    )


def test_sort_articles_for_processing_uses_recency_not_source_order() -> None:
    older_first_source = article("old", "iacr-eprint", datetime(2025, 1, 1, tzinfo=UTC))
    newer_later_source = article("new", "cloudflare-blog", datetime(2026, 6, 1, tzinfo=UTC))

    sorted_articles = sort_articles_for_processing([older_first_source, newer_later_source])

    assert sorted_articles == [newer_later_source, older_first_source]


def test_sort_articles_for_processing_falls_back_to_fetched_at() -> None:
    no_published = article("no-date", "nist", None)
    older_published = article("old", "iacr-eprint", datetime(2025, 1, 1, tzinfo=UTC))

    sorted_articles = sort_articles_for_processing([older_published, no_published])

    assert sorted_articles[0] == no_published

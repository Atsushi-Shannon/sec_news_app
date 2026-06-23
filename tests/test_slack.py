from __future__ import annotations

from datetime import UTC, datetime

from crypto_radar.models import Article
from crypto_radar.outputs.slack import build_message


def test_build_message_includes_visible_separators() -> None:
    item = Article(
        id="1",
        title="Side-channel paper",
        url="https://example.com/paper",
        normalized_url="https://example.com/paper",
        source_id="test",
        source_name="Test Source",
        source_type="rss",
        content_type="Paper",
        published_at=datetime(2026, 6, 23, tzinfo=UTC),
        fetched_at=datetime(2026, 6, 23, tzinfo=UTC),
        summary="A useful summary.",
        categories=["Side-Channel"],
        matched_keywords=["side-channel"],
        score=12,
        fingerprint="fp",
    )

    message = build_message(item, notion_result="sent")

    assert message.startswith("Crypto Research Radar\n---\n")
    assert message.rstrip().endswith("---")

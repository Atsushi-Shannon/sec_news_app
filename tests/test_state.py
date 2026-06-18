from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from crypto_radar.models import Article
from crypto_radar.state import StateFileError, StateStore


def article() -> Article:
    return Article(
        id="1",
        title="Title",
        url="https://example.com/a",
        normalized_url="https://example.com/a",
        source_id="test",
        source_name="Test",
        source_type="rss",
        content_type="News",
        published_at=None,
        fetched_at=datetime(2026, 6, 18, tzinfo=UTC),
        score=8,
        fingerprint="fp",
    )


def test_state_new_file_is_created_in_memory(tmp_path) -> None:
    store = StateStore(tmp_path / "seen_items.json")
    data = store.load()
    assert data.items == {}


def test_state_save_and_load(tmp_path) -> None:
    path = tmp_path / "seen_items.json"
    store = StateStore(path)
    store.load()
    store.record(article(), sent_to_notion=True, sent_to_slack=False)
    store.save()

    loaded = StateStore(path)
    loaded.load()
    assert loaded.has_seen(article())
    assert loaded.data.items["fp"].sent_to_notion is True


def test_state_dry_run_does_not_change_items(tmp_path) -> None:
    store = StateStore(tmp_path / "seen_items.json")
    store.load()
    store.record(article(), sent_to_notion=True, sent_to_slack=True, dry_run=True)
    assert store.data.items == {}


def test_state_invalid_json_raises(tmp_path) -> None:
    path = tmp_path / "seen_items.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(StateFileError):
        StateStore(path).load()


def test_state_save_writes_valid_json(tmp_path) -> None:
    path = tmp_path / "seen_items.json"
    store = StateStore(path)
    store.load()
    store.record(article(), sent_to_notion=False, sent_to_slack=False)
    store.save()
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1

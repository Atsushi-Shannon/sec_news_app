from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from crypto_radar.models import Article
from crypto_radar.utils.dates import ensure_utc, isoformat_utc, now_utc, parse_datetime


class StateFileError(RuntimeError):
    pass


class SeenItem(BaseModel):
    url: str
    title: str
    source_id: str
    published_at: str | None = None
    processed_at: str
    score: int
    sent_to_notion: bool = False
    sent_to_slack: bool = False


class StateData(BaseModel):
    version: int = 1
    items: dict[str, SeenItem] = Field(default_factory=dict)


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = StateData()

    def load(self) -> StateData:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.data = StateData()
            return self.data
        try:
            with self.path.open("r", encoding="utf-8") as file:
                raw = json.load(file)
        except json.JSONDecodeError as exc:
            raise StateFileError(f"State file is not valid JSON: {self.path}") from exc
        except OSError as exc:
            raise StateFileError(f"Could not read state file {self.path}: {exc}") from exc
        try:
            self.data = StateData.model_validate(raw)
        except ValidationError as exc:
            raise StateFileError(f"State file has invalid structure: {self.path}: {exc}") from exc
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.data.model_dump(mode="json")
        temp_path = self.path.with_name(f".{self.path.name}.tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2, sort_keys=True)
                file.write("\n")
            os.replace(temp_path, self.path)
        except OSError as exc:
            raise StateFileError(f"Could not save state file {self.path}: {exc}") from exc

    def fingerprints(self) -> set[str]:
        return set(self.data.items)

    def has_seen(self, article: Article) -> bool:
        return article.fingerprint in self.data.items

    def record(
        self,
        article: Article,
        *,
        sent_to_notion: bool,
        sent_to_slack: bool,
        dry_run: bool = False,
    ) -> None:
        if dry_run:
            return
        self.data.items[article.fingerprint] = SeenItem(
            url=article.normalized_url or article.url,
            title=article.title,
            source_id=article.source_id,
            published_at=isoformat_utc(article.published_at),
            processed_at=isoformat_utc(now_utc()) or "",
            score=article.score,
            sent_to_notion=sent_to_notion,
            sent_to_slack=sent_to_slack,
        )

    def cleanup(self, *, older_than_days: int = 365, low_score_below: int = 5) -> int:
        cutoff = now_utc() - timedelta(days=older_than_days)
        removed = 0
        for fingerprint, item in list(self.data.items.items()):
            processed_at = parse_datetime(item.processed_at)
            if processed_at is None:
                continue
            if ensure_utc(processed_at) < cutoff and item.score < low_score_below:
                del self.data.items[fingerprint]
                removed += 1
        return removed


def state_from_json(raw: dict[str, Any]) -> StateData:
    return StateData.model_validate(raw)

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import feedparser
import httpx

from crypto_radar.collectors.base import USER_AGENT
from crypto_radar.models import RawItem, SourceConfig
from crypto_radar.utils.dates import datetime_from_struct, now_utc
from crypto_radar.utils.urls import is_safe_http_url

logger = logging.getLogger(__name__)


class FeedFetchError(RuntimeError):
    pass


class RSSCollector:
    def __init__(self, source: SourceConfig, *, timeout: float = 20.0) -> None:
        self.source = source
        self.timeout = timeout

    def collect(self, limit: int | None = None) -> list[RawItem]:
        if not self.source.url:
            raise FeedFetchError(f"RSS source {self.source.id} has no URL")
        if not is_safe_http_url(self.source.url):
            raise FeedFetchError(f"RSS source {self.source.id} has unsafe URL")

        logger.debug("Fetching RSS source %s", self.source.id)
        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                max_redirects=5,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = client.get(self.source.url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise FeedFetchError(f"Timeout fetching {self.source.id}") from exc
        except httpx.RequestError as exc:
            raise FeedFetchError(f"Connection error fetching {self.source.id}: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise FeedFetchError(f"HTTP {status} fetching {self.source.id}") from exc

        parsed = feedparser.parse(response.content)
        if parsed.bozo:
            logger.warning("Feed parser warning for %s: %s", self.source.id, parsed.bozo_exception)

        fetched_at = now_utc()
        entries = parsed.entries[: limit or self.source.max_results or len(parsed.entries)]
        return [self._entry_to_raw(entry, fetched_at) for entry in entries]

    def _entry_to_raw(self, entry: Any, fetched_at: datetime) -> RawItem:
        url = _first_non_empty(
            getattr(entry, "link", None),
            _alternate_link(entry),
            getattr(entry, "id", None),
        )
        authors = _authors(entry)
        summary = _first_non_empty(
            getattr(entry, "summary", None),
            getattr(entry, "description", None),
            getattr(entry, "subtitle", None),
        )
        published = datetime_from_struct(
            getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        )
        return RawItem(
            source_id=self.source.id,
            source_name=self.source.name,
            source_type=self.source.type,
            content_type=self.source.content_type,
            title=str(getattr(entry, "title", "") or "").strip(),
            url=str(url or "").strip(),
            published_at=published,
            fetched_at=fetched_at,
            authors=authors,
            summary=str(summary or "").strip(),
            language=getattr(entry, "language", None),
            raw_id=getattr(entry, "id", None),
            default_categories=list(self.source.default_categories),
        )


def _authors(entry: Any) -> list[str]:
    authors: list[str] = []
    for author in getattr(entry, "authors", []) or []:
        name = author.get("name") if isinstance(author, dict) else getattr(author, "name", None)
        if name:
            authors.append(str(name))
    if not authors and getattr(entry, "author", None):
        authors.append(str(entry.author))
    return authors


def _alternate_link(entry: Any) -> str | None:
    for link in getattr(entry, "links", []) or []:
        rel = link.get("rel") if isinstance(link, dict) else getattr(link, "rel", None)
        href = link.get("href") if isinstance(link, dict) else getattr(link, "href", None)
        if href and (rel in {None, "alternate"}):
            return str(href)
    return None


def _first_non_empty(*values: object) -> object | None:
    for value in values:
        if value:
            return value
    return None

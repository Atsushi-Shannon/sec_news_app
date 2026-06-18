from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlencode

import feedparser
import httpx

from crypto_radar.collectors.base import USER_AGENT
from crypto_radar.collectors.rss import FeedFetchError
from crypto_radar.models import RawItem, SourceConfig
from crypto_radar.utils.dates import datetime_from_struct, now_utc
from crypto_radar.utils.urls import is_safe_http_url

logger = logging.getLogger(__name__)


class ArxivCollector:
    def __init__(self, source: SourceConfig, *, timeout: float = 20.0) -> None:
        self.source = source
        self.timeout = timeout

    def collect(self, limit: int | None = None) -> list[RawItem]:
        if not self.source.url:
            raise FeedFetchError(f"arXiv source {self.source.id} has no API URL")
        if not self.source.query:
            raise FeedFetchError(f"arXiv source {self.source.id} has no query")
        if not is_safe_http_url(self.source.url):
            raise FeedFetchError(f"arXiv source {self.source.id} has unsafe URL")

        max_results = limit or self.source.max_results or 50
        params = {
            "search_query": self.source.query,
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "lastUpdatedDate",
            "sortOrder": "descending",
        }
        request_url = f"{self.source.url}?{urlencode(params)}"
        logger.debug("Fetching arXiv source %s", self.source.id)
        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                max_redirects=5,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = client.get(request_url)
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
            logger.warning("arXiv parser warning for %s: %s", self.source.id, parsed.bozo_exception)

        fetched_at = now_utc()
        return [self._entry_to_raw(entry, fetched_at) for entry in parsed.entries[:max_results]]

    def _entry_to_raw(self, entry: object, fetched_at: datetime) -> RawItem:
        authors = []
        for author in getattr(entry, "authors", []) or []:
            name = author.get("name") if isinstance(author, dict) else getattr(author, "name", None)
            if name:
                authors.append(str(name))
        published = datetime_from_struct(
            getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        )
        return RawItem(
            source_id=self.source.id,
            source_name=self.source.name,
            source_type=self.source.type,
            content_type=self.source.content_type,
            title=str(getattr(entry, "title", "") or "").strip(),
            url=str(getattr(entry, "link", "") or "").strip(),
            published_at=published,
            fetched_at=fetched_at,
            authors=authors,
            summary=str(getattr(entry, "summary", "") or "").strip(),
            language=getattr(entry, "language", None),
            raw_id=getattr(entry, "id", None),
            default_categories=list(self.source.default_categories),
        )

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from crypto_radar.models import Article, NotionProperties
from crypto_radar.utils.dates import isoformat_utc, now_utc
from crypto_radar.utils.urls import is_safe_http_url

logger = logging.getLogger(__name__)

NOTION_BASE_URL = "https://api.notion.com/v1"
RICH_TEXT_LIMIT = 1900
TITLE_LIMIT = 2000


class NotionError(RuntimeError):
    pass


@dataclass
class NotionSendResult:
    sent: bool
    skipped_existing: bool = False
    page_id: str | None = None
    message: str = ""


class NotionClient:
    def __init__(
        self,
        *,
        token: str,
        database_id: str,
        api_version: str,
        properties: NotionProperties,
        timeout: float = 20.0,
    ) -> None:
        self.token = token
        self.database_id = database_id
        self.api_version = api_version
        self.properties = properties
        self.timeout = timeout

    @classmethod
    def from_env(
        cls,
        *,
        api_version_default: str,
        properties: NotionProperties,
    ) -> NotionClient | None:
        token = os.getenv("NOTION_API_TOKEN")
        database_id = os.getenv("NOTION_DATABASE_ID")
        if not token or not database_id:
            logger.warning(
                "Notion is disabled because NOTION_API_TOKEN or NOTION_DATABASE_ID is unset"
            )
            return None
        return cls(
            token=token,
            database_id=database_id,
            api_version=os.getenv("NOTION_API_VERSION") or api_version_default,
            properties=properties,
        )

    def has_fingerprint(self, fingerprint: str) -> bool:
        payload = {
            "filter": {
                "property": self.properties.fingerprint,
                "rich_text": {"equals": fingerprint},
            },
            "page_size": 1,
        }
        data = self._request("POST", f"/databases/{self.database_id}/query", json=payload)
        return bool(data.get("results"))

    def send_article(self, article: Article, *, slack_notified: bool = False) -> NotionSendResult:
        if self.has_fingerprint(article.fingerprint):
            logger.info("Notion already has fingerprint for %s", article.title)
            return NotionSendResult(sent=True, skipped_existing=True, message="already exists")

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": self._article_properties(article, slack_notified=slack_notified),
        }
        data = self._request("POST", "/pages", json=payload)
        return NotionSendResult(sent=True, page_id=data.get("id"), message="created")

    def _request(self, method: str, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": self.api_version,
        }
        url = f"{NOTION_BASE_URL}{path}"
        attempts = 4
        delay = 1.0
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            for attempt in range(1, attempts + 1):
                try:
                    response = client.request(method, url, json=json)
                except httpx.TimeoutException as exc:
                    if attempt == attempts:
                        raise NotionError(f"Notion timeout after {attempts} attempts") from exc
                    time.sleep(delay)
                    delay *= 2
                    continue
                except httpx.RequestError as exc:
                    if attempt == attempts:
                        raise NotionError(f"Notion request failed: {exc}") from exc
                    time.sleep(delay)
                    delay *= 2
                    continue

                if response.status_code == 429 and attempt < attempts:
                    retry_after = response.headers.get("Retry-After")
                    sleep_for = _retry_after_seconds(retry_after) or delay
                    logger.warning("Notion rate limited; retrying after %.1fs", sleep_for)
                    time.sleep(sleep_for)
                    delay *= 2
                    continue
                if 500 <= response.status_code < 600 and attempt < attempts:
                    logger.warning("Notion server error HTTP %s; retrying", response.status_code)
                    time.sleep(delay)
                    delay *= 2
                    continue
                if 400 <= response.status_code < 500:
                    raise NotionError(
                        f"Notion API returned HTTP {response.status_code}: {_safe_response_text(response)}"
                    )
                if response.status_code >= 500:
                    raise NotionError(
                        f"Notion API returned HTTP {response.status_code}: {_safe_response_text(response)}"
                    )
                return response.json()
        raise NotionError("Notion request failed")

    def _article_properties(self, article: Article, *, slack_notified: bool) -> dict[str, Any]:
        props = self.properties
        properties: dict[str, Any] = {
            props.name: {"title": [{"text": {"content": truncate(article.title, TITLE_LIMIT)}}]},
            props.url: {"url": article.url if is_safe_http_url(article.url) else None},
            props.source: {"select": {"name": truncate(article.source_name, 100)}},
            props.content_type: {"select": {"name": article.content_type}},
            props.research_area: {
                "multi_select": [
                    {"name": truncate(category, 100)} for category in article.categories
                ]
            },
            props.score: {"number": article.score},
            props.summary: {"rich_text": rich_text(article.summary)},
            props.relevance: {"rich_text": rich_text(relevance_text(article))},
            props.added_at: {"date": {"start": isoformat_utc(now_utc())}},
            props.slack_notified: {"checkbox": slack_notified},
            props.fingerprint: {"rich_text": rich_text(article.fingerprint)},
        }
        if article.published_at:
            properties[props.published] = {"date": {"start": isoformat_utc(article.published_at)}}
        else:
            properties[props.published] = {"date": None}
        status_value = {"name": "New"}
        properties[props.status] = {props.status_property_type: status_value}
        return properties


def relevance_text(article: Article) -> str:
    categories = ", ".join(article.categories) or "None"
    keywords = ", ".join(article.matched_keywords) or "None"
    reasons = ", ".join(article.score_reasons) or "None"
    return (
        f"Matched categories: {categories}\nMatched keywords: {keywords}\nScore reasons: {reasons}"
    )


def rich_text(value: str) -> list[dict[str, Any]]:
    text = truncate(value, RICH_TEXT_LIMIT)
    if not text:
        return []
    return [{"text": {"content": text}}]


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)] + "..."


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _safe_response_text(response: httpx.Response) -> str:
    text = response.text[:500]
    for header in ("Authorization", "authorization"):
        text = text.replace(header, "***")
    return text

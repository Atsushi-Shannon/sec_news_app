from __future__ import annotations

import logging
import os

import httpx

from crypto_radar.models import Article
from crypto_radar.outputs.notion import truncate
from crypto_radar.utils.dates import isoformat_utc
from crypto_radar.utils.urls import is_safe_http_url

logger = logging.getLogger(__name__)

SLACK_TEXT_LIMIT = 3500


class SlackError(RuntimeError):
    pass


class SlackNotifier:
    def __init__(self, webhook_url: str, *, timeout: float = 15.0) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> SlackNotifier | None:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("Slack is disabled because SLACK_WEBHOOK_URL is unset")
            return None
        if not is_safe_http_url(webhook_url):
            logger.warning("Slack is disabled because SLACK_WEBHOOK_URL is not an HTTP(S) URL")
            return None
        return cls(webhook_url)

    def send_article(self, article: Article, *, notion_result: str) -> None:
        payload = {"text": build_message(article, notion_result=notion_result)}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.webhook_url, json=payload)
        except httpx.TimeoutException as exc:
            raise SlackError("Slack webhook timed out") from exc
        except httpx.RequestError as exc:
            raise SlackError(f"Slack webhook request failed: {exc}") from exc
        if response.status_code >= 400:
            raise SlackError(
                f"Slack webhook returned HTTP {response.status_code}: {response.text[:300]}"
            )


def build_message(article: Article, *, notion_result: str) -> str:
    published = isoformat_utc(article.published_at) or "Unknown"
    categories = ", ".join(article.categories) or "None"
    matched = ", ".join(article.matched_keywords) or "None"
    summary = truncate(article.summary, 500)
    original_url = article.url if is_safe_http_url(article.url) else article.normalized_url
    text = f"""Crypto Research Radar

{article.title}

Source: {article.source_name}
Published: {published}
Score: {article.score}
Categories: {categories}
Matched: {matched}
Notion: {notion_result}

{summary}

Original:
{original_url}
"""
    return truncate(text, SLACK_TEXT_LIMIT)

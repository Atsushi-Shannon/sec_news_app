from __future__ import annotations

import hashlib
import html
import re

from crypto_radar.models import Article, RawItem
from crypto_radar.utils.urls import normalize_url

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def raw_to_article(raw: RawItem) -> Article:
    title = normalize_text(raw.title)
    summary = clean_summary(raw.summary)
    normalized_url = normalize_url(raw.url)
    article_id = raw.raw_id or normalized_url or title
    fingerprint = make_fingerprint(
        source_id=raw.source_id,
        normalized_url=normalized_url,
        title=title,
    )
    return Article(
        id=article_id,
        title=title,
        url=raw.url,
        normalized_url=normalized_url,
        source_id=raw.source_id,
        source_name=raw.source_name,
        source_type=raw.source_type,
        content_type=raw.content_type,
        published_at=raw.published_at,
        fetched_at=raw.fetched_at,
        authors=raw.authors,
        summary=summary,
        language=raw.language,
        categories=list(dict.fromkeys(raw.default_categories)),
        fingerprint=fingerprint,
    )


def clean_summary(value: str) -> str:
    unescaped = html.unescape(value or "")
    without_tags = HTML_TAG_RE.sub(" ", unescaped)
    return normalize_text(without_tags)


def normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value or "").strip()


def normalize_title_for_fingerprint(value: str) -> str:
    lowered = normalize_text(value).casefold()
    return re.sub(r"[^\w\s-]", "", lowered).strip()


def make_fingerprint(*, source_id: str, normalized_url: str, title: str) -> str:
    title_key = normalize_title_for_fingerprint(title)
    key = f"{source_id.casefold()}|{normalized_url}|{title_key}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

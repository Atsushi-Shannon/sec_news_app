from __future__ import annotations

import hashlib

from crypto_radar.models import Article
from crypto_radar.normalize import normalize_title_for_fingerprint


def canonical_article_key(article: Article) -> str:
    url_key = article.normalized_url or article.url
    title_key = normalize_title_for_fingerprint(article.title)
    key = f"{url_key}|{title_key}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def deduplicate_articles(
    articles: list[Article],
    *,
    seen_fingerprints: set[str] | None = None,
) -> tuple[list[Article], list[Article]]:
    seen_fingerprints = seen_fingerprints or set()
    batch_fingerprints: set[str] = set()
    batch_canonical: set[str] = set()
    unique: list[Article] = []
    duplicates: list[Article] = []

    for article in articles:
        canonical = canonical_article_key(article)
        if (
            article.fingerprint in seen_fingerprints
            or article.fingerprint in batch_fingerprints
            or canonical in batch_canonical
        ):
            duplicates.append(article)
            continue
        unique.append(article)
        batch_fingerprints.add(article.fingerprint)
        batch_canonical.add(canonical)

    return unique, duplicates

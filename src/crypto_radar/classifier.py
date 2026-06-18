from __future__ import annotations

import re

from crypto_radar.models import Article, ClassificationResult, KeywordsConfig


def classify_article(article: Article, keywords: KeywordsConfig) -> ClassificationResult:
    title = article.title or ""
    summary = article.summary or ""
    categories = list(article.categories)
    matched_keywords: list[str] = []
    title_keywords: list[str] = []
    summary_keywords: list[str] = []
    negative_matches: list[str] = []

    for category, config in keywords.categories.items():
        category_matched = False
        for keyword in config.keywords:
            in_title = keyword_matches(keyword, title)
            in_summary = keyword_matches(keyword, summary)
            if not in_title and not in_summary:
                continue
            category_matched = True
            add_unique(matched_keywords, keyword)
            if in_title:
                add_unique(title_keywords, keyword)
            if in_summary:
                add_unique(summary_keywords, keyword)
        if category_matched:
            add_unique(categories, category)

    for negative in keywords.negative_keywords:
        if keyword_matches(negative.keyword, title) or keyword_matches(negative.keyword, summary):
            add_unique(negative_matches, negative.keyword)
            add_unique(matched_keywords, negative.keyword)

    return ClassificationResult(
        categories=categories,
        matched_keywords=matched_keywords,
        title_keywords=title_keywords,
        summary_keywords=summary_keywords,
        negative_keywords=negative_matches,
    )


def keyword_matches(keyword: str, text: str) -> bool:
    if not keyword or not text:
        return False
    if _is_ascii_keyword(keyword):
        pattern = _ascii_keyword_pattern(keyword)
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    return keyword.casefold() in text.casefold()


def _is_ascii_keyword(keyword: str) -> bool:
    return all(ord(character) < 128 for character in keyword)


def _ascii_keyword_pattern(keyword: str) -> str:
    escaped = re.escape(keyword)
    return rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])"


def add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)

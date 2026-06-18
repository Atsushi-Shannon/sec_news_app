from __future__ import annotations

from datetime import datetime

from crypto_radar.models import (
    Article,
    ClassificationResult,
    KeywordsConfig,
    ScoreResult,
    ScoringConfig,
    SourceConfig,
)
from crypto_radar.utils.dates import is_recent, now_utc


def score_article(
    article: Article,
    source: SourceConfig,
    classification: ClassificationResult,
    keywords: KeywordsConfig,
    scoring: ScoringConfig,
    *,
    current_time: datetime | None = None,
) -> ScoreResult:
    score = source.base_score
    reasons = [f"base_score:{source.base_score}"]
    title_multiplier = scoring.bonuses.keyword_in_title_multiplier

    for category in classification.categories:
        category_config = keywords.categories.get(category)
        if category_config is None:
            continue
        category_keywords = set(category_config.keywords)
        has_title = bool(category_keywords.intersection(classification.title_keywords))
        has_summary = bool(category_keywords.intersection(classification.summary_keywords))
        if not has_title and not has_summary:
            continue
        if has_title:
            points = category_config.weight * title_multiplier
            reasons.append(f"{category}:title_keyword:{points}")
        else:
            points = category_config.weight
            reasons.append(f"{category}:summary_keyword:{points}")
        score += points

    for negative in keywords.negative_keywords:
        if negative.keyword in classification.negative_keywords:
            score += negative.weight
            reasons.append(f"negative:{negative.keyword}:{negative.weight}")

    category_count = len(
        [category for category in classification.categories if category in keywords.categories]
    )
    multiple = scoring.bonuses.multiple_category_bonus
    if category_count >= multiple.min_categories:
        score += multiple.score
        reasons.append(f"multiple_categories:{multiple.score}")

    recent = scoring.bonuses.recent_publication_bonus
    if is_recent(
        article.published_at, now=current_time or now_utc(), within_hours=recent.within_hours
    ):
        score += recent.score
        reasons.append(f"recent:{recent.score}")

    return ScoreResult(score=score, reasons=reasons)


def apply_classification_and_score(
    article: Article,
    classification: ClassificationResult,
    score: ScoreResult,
) -> Article:
    article.categories = classification.categories
    article.matched_keywords = classification.matched_keywords
    article.negative_matches = classification.negative_keywords
    article.score = score.score
    article.score_reasons = score.reasons
    return article


def above_notion_threshold(article: Article, scoring: ScoringConfig) -> bool:
    return article.score >= scoring.thresholds.notion


def above_slack_threshold(article: Article, scoring: ScoringConfig) -> bool:
    return article.score >= scoring.thresholds.slack

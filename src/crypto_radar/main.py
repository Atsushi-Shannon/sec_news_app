from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path

from crypto_radar.classifier import classify_article
from crypto_radar.collectors.arxiv import ArxivCollector
from crypto_radar.collectors.rss import FeedFetchError, RSSCollector
from crypto_radar.config import (
    ConfigError,
    default_config_dir,
    load_environment,
    load_keywords,
    load_scoring,
    load_sources,
    state_file_path,
)
from crypto_radar.deduplicate import deduplicate_articles
from crypto_radar.logging_config import setup_logging
from crypto_radar.models import Article, KeywordsConfig, ScoringConfig, SourceConfig
from crypto_radar.normalize import raw_to_article
from crypto_radar.outputs.notion import NotionClient, NotionError
from crypto_radar.outputs.slack import SlackError, SlackNotifier, build_message
from crypto_radar.scorer import (
    above_notion_threshold,
    above_slack_threshold,
    apply_classification_and_score,
    score_article,
)
from crypto_radar.state import StateFileError, StateStore
from crypto_radar.utils.dates import ensure_utc

logger = logging.getLogger(__name__)


@dataclass
class RunStats:
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    items_fetched: int = 0
    duplicates_skipped: int = 0
    items_scored: int = 0
    sent_to_notion: int = 0
    sent_to_slack: int = 0
    errors: int = 0
    failed_sources: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect cryptography/security research updates.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not write to Notion, Slack, or state"
    )
    parser.add_argument("--source", help="Only run a single source id")
    parser.add_argument("--limit", type=int, help="Limit items per source and overall processing")
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_environment()
    setup_logging("DEBUG" if args.verbose else None)

    try:
        run(args)
    except (ConfigError, StateFileError) as exc:
        logger.error("%s", exc)
        raise SystemExit(2) from exc


def run(args: argparse.Namespace) -> RunStats:
    config_dir: Path = args.config_dir
    sources_config = load_sources(config_dir / "sources.yaml")
    keywords = load_keywords(config_dir / "keywords.yaml")
    scoring = load_scoring(config_dir / "scoring.yaml")

    state = StateStore(state_file_path())
    state.load()

    sources = [
        source
        for source in sources_config.sources
        if source.enabled and (args.source is None or source.id == args.source)
    ]
    if args.source and not sources:
        logger.warning("No enabled source matched --source %s", args.source)

    stats = RunStats()
    articles = collect_and_score_sources(
        sources=sources,
        keywords=keywords,
        scoring=scoring,
        limit=args.limit,
        stats=stats,
    )
    max_items = args.limit or scoring.limits.max_items_per_run
    articles = sort_articles_for_processing(articles)[:max_items]
    unique_articles, duplicate_articles = deduplicate_articles(
        articles,
        seen_fingerprints=state.fingerprints(),
    )
    stats.duplicates_skipped += len(duplicate_articles)
    logger.info("New items after deduplication: %s", len(unique_articles))

    notion_candidates = [
        article for article in unique_articles if above_notion_threshold(article, scoring)
    ][: scoring.limits.max_notion_items_per_run]
    slack_candidates = [
        article for article in notion_candidates if above_slack_threshold(article, scoring)
    ][: scoring.limits.max_slack_notifications_per_run]

    log_dry_run_details(
        unique_articles=unique_articles,
        notion_candidates=notion_candidates,
        slack_candidates=slack_candidates,
        dry_run=args.dry_run,
    )

    sent_to_notion: dict[str, bool] = {}
    sent_to_slack: dict[str, bool] = {}

    if not args.dry_run:
        notion_client = NotionClient.from_env(
            api_version_default=scoring.notion.api_version_default,
            properties=scoring.notion.properties,
        )
        slack_notifier = SlackNotifier.from_env()

        for article in notion_candidates:
            sent_to_notion[article.fingerprint] = send_to_notion(article, notion_client, stats)

        for article in slack_candidates:
            notion_status = "sent" if sent_to_notion.get(article.fingerprint) else "not sent"
            sent_to_slack[article.fingerprint] = send_to_slack(
                article,
                slack_notifier,
                stats,
                notion_result=notion_status,
            )

        for article in unique_articles:
            state.record(
                article,
                sent_to_notion=sent_to_notion.get(article.fingerprint, False),
                sent_to_slack=sent_to_slack.get(article.fingerprint, False),
            )
        removed = state.cleanup(low_score_below=scoring.thresholds.notion)
        if removed:
            logger.info("Cleaned up %s old low-score state items", removed)
        state.save()
    else:
        for article in slack_candidates:
            logger.info(
                "Dry-run Slack payload for %s:\n%s",
                article.title,
                build_message(article, notion_result="dry-run"),
            )

    log_summary(stats)
    return stats


def collect_and_score_sources(
    *,
    sources: list[SourceConfig],
    keywords: KeywordsConfig,
    scoring: ScoringConfig,
    limit: int | None,
    stats: RunStats,
) -> list[Article]:
    articles: list[Article] = []
    source_by_id = {source.id: source for source in sources}
    for source in sources:
        stats.sources_attempted += 1
        try:
            collector = collector_for_source(source)
            raw_items = collector.collect(limit=limit or source.max_results)
            stats.sources_succeeded += 1
            stats.items_fetched += len(raw_items)
        except FeedFetchError as exc:
            stats.sources_failed += 1
            stats.errors += 1
            stats.failed_sources.append(source.id)
            logger.warning("Skipping source %s: %s", source.id, exc)
            continue

        for raw in raw_items:
            article = raw_to_article(raw)
            classification = classify_article(article, keywords)
            score = score_article(
                article,
                source_by_id[article.source_id],
                classification,
                keywords,
                scoring,
            )
            articles.append(apply_classification_and_score(article, classification, score))
            stats.items_scored += 1
    return articles


def collector_for_source(source: SourceConfig) -> RSSCollector | ArxivCollector:
    if source.type == "rss":
        return RSSCollector(source)
    if source.type == "arxiv":
        return ArxivCollector(source)
    raise FeedFetchError(f"Unsupported source type: {source.type}")


def sort_articles_for_processing(articles: list[Article]) -> list[Article]:
    return sorted(
        articles,
        key=lambda article: ensure_utc(article.published_at or article.fetched_at),
        reverse=True,
    )


def send_to_notion(
    article: Article,
    notion_client: NotionClient | None,
    stats: RunStats,
) -> bool:
    if notion_client is None:
        return False
    try:
        result = notion_client.send_article(article)
    except NotionError as exc:
        stats.errors += 1
        logger.error("Notion failed for %s: %s", article.title, exc)
        return False
    if result.sent:
        stats.sent_to_notion += 1
        logger.info("Notion %s for %s", result.message, article.title)
    return result.sent


def send_to_slack(
    article: Article,
    slack_notifier: SlackNotifier | None,
    stats: RunStats,
    *,
    notion_result: str,
) -> bool:
    if slack_notifier is None:
        return False
    try:
        slack_notifier.send_article(article, notion_result=notion_result)
    except SlackError as exc:
        stats.errors += 1
        logger.error("Slack failed for %s: %s", article.title, exc)
        return False
    stats.sent_to_slack += 1
    logger.info("Slack notified for %s", article.title)
    return True


def log_dry_run_details(
    *,
    unique_articles: list[Article],
    notion_candidates: list[Article],
    slack_candidates: list[Article],
    dry_run: bool,
) -> None:
    logger.info("Notion candidates: %s", len(notion_candidates))
    logger.info("Slack candidates: %s", len(slack_candidates))
    if not dry_run:
        return
    for article in unique_articles:
        logger.info(
            "Dry-run item score=%s source=%s title=%s categories=%s matched=%s negative=%s reasons=%s",
            article.score,
            article.source_name,
            article.title,
            article.categories,
            article.matched_keywords,
            article.negative_matches,
            article.score_reasons,
        )


def log_summary(stats: RunStats) -> None:
    logger.info(
        "Run summary:\n"
        "Sources attempted: %s\n"
        "Sources succeeded: %s\n"
        "Sources failed: %s\n"
        "Items fetched: %s\n"
        "Duplicates skipped: %s\n"
        "Items scored: %s\n"
        "Sent to Notion: %s\n"
        "Sent to Slack: %s\n"
        "Errors: %s",
        stats.sources_attempted,
        stats.sources_succeeded,
        stats.sources_failed,
        stats.items_fetched,
        stats.duplicates_skipped,
        stats.items_scored,
        stats.sent_to_notion,
        stats.sent_to_slack,
        stats.errors,
    )
    if stats.failed_sources:
        logger.info("Failed sources: %s", ", ".join(stats.failed_sources))


if __name__ == "__main__":
    main()

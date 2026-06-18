from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SourceType = Literal["rss", "arxiv"]
ContentType = Literal[
    "Paper",
    "News",
    "Standard",
    "Press Release",
    "Advisory",
    "Blog",
    "Other",
]


class SourceConfig(BaseModel):
    id: str
    name: str
    type: SourceType
    content_type: ContentType = "Other"
    url: str | None = None
    query: str | None = None
    enabled: bool = True
    base_score: int = 0
    max_results: int | None = None
    default_categories: list[str] = Field(default_factory=list)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        # Pydantic keeps this as a string for easier YAML round-tripping.
        HttpUrl(value)
        return value


class SourcesConfig(BaseModel):
    sources: list[SourceConfig]


class CategoryKeywords(BaseModel):
    weight: int
    keywords: list[str]


class NegativeKeyword(BaseModel):
    keyword: str
    weight: int


class KeywordsConfig(BaseModel):
    categories: dict[str, CategoryKeywords]
    negative_keywords: list[NegativeKeyword] = Field(default_factory=list)


class MultipleCategoryBonus(BaseModel):
    min_categories: int = 2
    score: int = 2


class RecentPublicationBonus(BaseModel):
    within_hours: int = 48
    score: int = 1


class ScoringThresholds(BaseModel):
    notion: int = 5
    slack: int = 10


class ScoringBonuses(BaseModel):
    keyword_in_title_multiplier: int = 2
    multiple_category_bonus: MultipleCategoryBonus = Field(default_factory=MultipleCategoryBonus)
    recent_publication_bonus: RecentPublicationBonus = Field(default_factory=RecentPublicationBonus)


class ScoringLimits(BaseModel):
    max_items_per_run: int = 100
    max_notion_items_per_run: int = 30
    max_slack_notifications_per_run: int = 5


class NotionProperties(BaseModel):
    name: str = "Name"
    url: str = "URL"
    published: str = "Published"
    source: str = "Source"
    content_type: str = "Content Type"
    research_area: str = "Research Area"
    score: str = "Score"
    status: str = "Status"
    status_property_type: Literal["status", "select"] = "status"
    summary: str = "Summary"
    relevance: str = "Relevance"
    added_at: str = "Added At"
    slack_notified: str = "Slack Notified"
    fingerprint: str = "Fingerprint"


class NotionConfig(BaseModel):
    api_version_default: str = "2022-06-28"
    properties: NotionProperties = Field(default_factory=NotionProperties)


class ScoringConfig(BaseModel):
    thresholds: ScoringThresholds = Field(default_factory=ScoringThresholds)
    bonuses: ScoringBonuses = Field(default_factory=ScoringBonuses)
    limits: ScoringLimits = Field(default_factory=ScoringLimits)
    notion: NotionConfig = Field(default_factory=NotionConfig)


class RawItem(BaseModel):
    source_id: str
    source_name: str
    source_type: SourceType
    content_type: ContentType
    title: str
    url: str
    published_at: datetime | None = None
    fetched_at: datetime
    authors: list[str] = Field(default_factory=list)
    summary: str = ""
    language: str | None = None
    raw_id: str | None = None
    default_categories: list[str] = Field(default_factory=list)


class Article(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str
    title: str
    url: str
    normalized_url: str
    source_id: str
    source_name: str
    source_type: str
    content_type: ContentType
    published_at: datetime | None
    fetched_at: datetime
    authors: list[str] = Field(default_factory=list)
    summary: str = ""
    language: str | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    score: int = 0
    fingerprint: str
    score_reasons: list[str] = Field(default_factory=list)
    negative_matches: list[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    categories: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    title_keywords: list[str] = Field(default_factory=list)
    summary_keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)


class ScoreResult(BaseModel):
    score: int
    reasons: list[str] = Field(default_factory=list)

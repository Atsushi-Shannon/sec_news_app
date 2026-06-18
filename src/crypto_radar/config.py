from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from crypto_radar.models import KeywordsConfig, ScoringConfig, SourcesConfig


class ConfigError(RuntimeError):
    pass


def load_environment(env_file: Path | None = None) -> None:
    load_dotenv(env_file)


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"Configuration file must contain a YAML mapping: {path}")
    return loaded


def load_sources(path: Path) -> SourcesConfig:
    try:
        return SourcesConfig.model_validate(read_yaml(path))
    except ValidationError as exc:
        raise ConfigError(f"Invalid sources configuration in {path}: {exc}") from exc


def load_keywords(path: Path) -> KeywordsConfig:
    try:
        return KeywordsConfig.model_validate(read_yaml(path))
    except ValidationError as exc:
        raise ConfigError(f"Invalid keywords configuration in {path}: {exc}") from exc


def load_scoring(path: Path) -> ScoringConfig:
    try:
        scoring = ScoringConfig.model_validate(read_yaml(path))
    except ValidationError as exc:
        raise ConfigError(f"Invalid scoring configuration in {path}: {exc}") from exc
    apply_threshold_overrides(scoring)
    return scoring


def apply_threshold_overrides(scoring: ScoringConfig) -> None:
    notion = os.getenv("NOTION_SCORE_THRESHOLD")
    slack = os.getenv("SLACK_SCORE_THRESHOLD")
    if notion:
        scoring.thresholds.notion = _parse_int_env("NOTION_SCORE_THRESHOLD", notion)
    if slack:
        scoring.thresholds.slack = _parse_int_env("SLACK_SCORE_THRESHOLD", slack)


def _parse_int_env(name: str, value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc


def state_file_path(default: str = "data/seen_items.json") -> Path:
    return Path(os.getenv("STATE_FILE") or default)


def default_config_dir() -> Path:
    return Path("config")

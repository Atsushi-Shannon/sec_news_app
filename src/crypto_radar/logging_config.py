from __future__ import annotations

import logging
import os
import time

SECRET_MARKERS = ("secret_", "ntn_", "xox", "hooks.slack.com")


class SecretMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        masked = mask_secrets(message)
        if masked != message:
            record.msg = masked
            record.args = ()
        return True


def mask_secrets(value: str) -> str:
    masked = value
    for env_name in ("NOTION_API_TOKEN", "SLACK_WEBHOOK_URL"):
        secret = os.getenv(env_name)
        if secret and secret in masked:
            masked = masked.replace(secret, "***")
    for marker in SECRET_MARKERS:
        if marker in masked:
            masked = _mask_marker(masked, marker)
    return masked


def _mask_marker(value: str, marker: str) -> str:
    index = value.find(marker)
    if index < 0:
        return value
    end = value.find(" ", index)
    if end < 0:
        end = len(value)
    return value[:index] + "***" + value[end:]


def setup_logging(level: str | None = None) -> None:
    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    numeric_level = getattr(logging, resolved, logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    logging.Formatter.converter = staticmethod(time.gmtime)
    root = logging.getLogger()
    masking_filter = SecretMaskingFilter()
    root.addFilter(masking_filter)
    for handler in root.handlers:
        handler.addFilter(masking_filter)

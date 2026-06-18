from __future__ import annotations

from typing import Protocol

from crypto_radar.models import RawItem

USER_AGENT = "crypto-research-radar/0.1 (+https://github.com/) python-httpx"


class Collector(Protocol):
    def collect(self, limit: int | None = None) -> list[RawItem]:
        """Collect raw items from one source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    url: str
    published_at: datetime
    summary: str


@dataclass(frozen=True)
class FetchResult:
    items: list[NewsItem]
    failures: list[str]

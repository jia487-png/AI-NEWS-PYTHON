from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

from .types import NewsItem

SOURCE_PRIORITY = {
    "TechCrunch": 0,
    "The Verge": 1,
    "Hacker News": 2,
}


def normalized_key(url: str) -> str:
    try:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower().removeprefix("www.")
        pathname = parsed.path.rstrip("/") or "/"
        return f"{hostname}{pathname}"
    except ValueError:
        return url.strip().lower()


def aggregate_articles(items: list[NewsItem], since: datetime) -> list[NewsItem]:
    by_key: dict[str, NewsItem] = {}
    for item in items:
        if item.published_at < since:
            continue
        key = normalized_key(item.url)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = item
            continue
        if SOURCE_PRIORITY.get(item.source, 99) < SOURCE_PRIORITY.get(existing.source, 99):
            by_key[key] = item

    return sorted(
        by_key.values(),
        key=lambda item: (item.published_at.timestamp(), SOURCE_PRIORITY.get(item.source, 99)),
        reverse=True,
    )

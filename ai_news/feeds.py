from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .text import clean_text, make_summary
from .types import FetchResult, NewsItem

USER_AGENT = "ai-news-daily-python/0.1"
HTTP_TIMEOUT_SECONDS = 15
HN_MAX_PAGES = 15
HN_PAGE_SIZE = 100

RSS_SOURCES = (
    {
        "name": "TechCrunch",
        "feed_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
    {
        "name": "The Verge",
        "feed_url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    },
)

AI_PATTERN = re.compile(
    r"\b(?:ai|llm|gpt|chatgpt|openai|anthropic|claude|gemini|deepseek|"
    r"mistral|llama|copilot|perplexity|midjourney|deepmind|sora|qwen|"
    r"xai|hugging\ face)\b|artificial intelligence|machine learning|"
    r"deep learning|large language model|language model|generative ai|"
    r"neural network|natural language processing|stable diffusion|"
    r"a\s*/\s*i\b",
    re.I,
)

_RSS_FETCH_LOCK = threading.Lock()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ElementTree.Element, name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == name:
            return "".join(child.itertext()).strip()
    return None


def _descendants(element: ElementTree.Element, name: str) -> Iterable[ElementTree.Element]:
    return (child for child in element.iter() if _local_name(child.tag) == name)


def _entry_link(element: ElementTree.Element) -> str | None:
    """Read RSS <link> text or the Atom <link href=...> attribute."""
    for child in element:
        if _local_name(child.tag) != "link":
            continue
        if child.attrib.get("href"):
            return child.attrib["href"].strip()
        text = "".join(child.itertext()).strip()
        if text:
            return text
    return None


def _entry_date(element: ElementTree.Element) -> datetime | None:
    for name in ("pubDate", "published", "updated", "date"):
        value = _child_text(element, name)
        if value:
            parsed = parse_datetime(value)
            if parsed:
                return parsed
    return None


def _entry_summary_candidates(element: ElementTree.Element) -> list[str]:
    candidates: list[str] = []
    for name in ("description", "summary", "content", "encoded", "body"):
        for child in element:
            if _local_name(child.tag) != name:
                continue
            if child.attrib.get("type") == "html":
                candidates.append("".join(child.itertext()))
            text = "".join(child.itertext()).strip()
            if text and text not in candidates:
                candidates.append(text)
    return candidates


def _request_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:  # noqa: S310
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None

    parsed: datetime | None = None
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        pass

    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def fetch_rss_source(source: dict[str, str], since: datetime) -> list[NewsItem]:
    xml_text = _request_text(source["feed_url"])
    # Feed content is not user-authored local XML, so the parser is safe here.
    with _RSS_FETCH_LOCK:
        root = ElementTree.fromstring(xml_text)  # noqa: S314
    items: list[NewsItem] = []
    entries = list(_descendants(root, "item")) + list(_descendants(root, "entry"))

    for entry in entries:
        title = _child_text(entry, "title")
        url = _entry_link(entry)
        published_at = _entry_date(entry)
        if not title or not url or not published_at or published_at < since:
            continue

        candidates = _entry_summary_candidates(entry)
        body = "\n\n".join(candidates)
        items.append(
            NewsItem(
                source=source["name"],
                title=title,
                url=url,
                published_at=published_at,
                summary=make_summary(body, title),
            )
        )

    return items


def _hit_title(hit: dict[str, Any]) -> str:
    return clean_text(hit.get("title") or "")


def _is_ai_relevant(hit: dict[str, Any]) -> bool:
    title = _hit_title(hit)
    if not title:
        return False
    if re.match(r"^(?:show|ask)\s+hn\s*:", title, re.I):
        return False
    story_text = clean_text(hit.get("story_text") or "")
    return bool(AI_PATTERN.search(f"{title} {story_text}"))


def fetch_hacker_news_ai(since: datetime) -> list[NewsItem]:
    # Hacker News has no official AI tag, so approximate the topic from its
    # newest submissions and keep only stories whose title/body mentions AI.
    since_unix = int(since.timestamp())
    hits: list[dict[str, Any]] = []

    for page in range(HN_MAX_PAGES):
        query = urlencode(
            {
                "tags": "story",
                "hitsPerPage": str(HN_PAGE_SIZE),
                "page": str(page),
                "numericFilters": f"created_at_i>{since_unix}",
            }
        )
        payload = _request_text(f"https://hn.algolia.com/api/v1/search_by_date?{query}")
        data = json.loads(payload)
        page_hits = data.get("hits") or []
        hits.extend(page_hits)

        last_page = max(0, int(data.get("nbPages") or 1) - 1)
        if page >= last_page or not page_hits:
            break

    items: list[NewsItem] = []
    for hit in hits:
        title = _hit_title(hit)
        published_at = parse_datetime(hit.get("created_at"))
        if not title or not published_at or published_at < since:
            continue
        if not _is_ai_relevant(hit):
            continue

        url = clean_text(hit.get("url") or "")
        if not url and hit.get("objectID"):
            url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
        if not url:
            continue

        items.append(
            NewsItem(
                source="Hacker News",
                title=title,
                url=url,
                published_at=published_at,
                summary=make_summary(hit.get("story_text") or "", title),
            )
        )

    return items


def _fetch_one(name: str, runner: Any) -> list[NewsItem]:
    try:
        return runner()
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(f"{name}: {error}") from error


def fetch_all_sources(since: datetime) -> FetchResult:
    tasks: list[tuple[str, Any]] = [
        (source["name"], lambda s=source: fetch_rss_source(s, since)) for source in RSS_SOURCES
    ]
    tasks.append(("Hacker News", lambda: fetch_hacker_news_ai(since)))

    items: list[NewsItem] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {
            executor.submit(_fetch_one, name, runner): name
            for name, runner in tasks
        }
        for future in as_completed(futures):
            try:
                items.extend(future.result())
            except Exception as error:  # noqa: BLE001
                failures.append(str(error))

    return FetchResult(items=items, failures=failures)

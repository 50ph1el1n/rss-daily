import hashlib
import html
import re
import unicodedata
from collections.abc import Iterable
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from .models import Article, Feed

TAIPEI = ZoneInfo("Asia/Taipei")
WHITESPACE = re.compile(r"\s+")
HTML_TAG = re.compile(r"<[^>]+>")


def clean_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = html.unescape(HTML_TAG.sub(" ", str(value)))
    text = WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()
    return text[:limit] or None


def normalize_url(value: str) -> str | None:
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return None
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return None
    host = parts.hostname.lower()
    port = parts.port
    if port and not (
        (parts.scheme.lower() == "http" and port == 80)
        or (parts.scheme.lower() == "https" and port == 443)
    ):
        host = f"{host}:{port}"
    if parts.username or parts.password:
        return None
    return urlunsplit((parts.scheme.lower(), host, parts.path or "/", parts.query, ""))


def parsed_time(entry: Any, name: str) -> tuple[datetime | None, str | None]:
    raw = entry.get(name)
    struct = entry.get(f"{name}_parsed")
    if not struct:
        return None, str(raw)[:500] if raw else None
    try:
        value = datetime(*struct[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None, str(raw)[:500] if raw else None
    return value, str(raw)[:500] if raw else None


def in_collection_date(value: datetime, collection_date: date) -> bool:
    return value.astimezone(TAIPEI).date() == collection_date


def _rfc3339(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def article_from_entry(entry: Any, feed: Feed, collection_date: date) -> Article | None:
    published, published_raw = parsed_time(entry, "published")
    updated, updated_raw = parsed_time(entry, "updated")
    effective = published or updated
    title = clean_text(entry.get("title"), 500)
    url = normalize_url(entry.get("link", ""))
    if not effective or not in_collection_date(effective, collection_date) or not title or not url:
        return None
    identity = "url\n" + url
    article_id = "sha256:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
    authors = sorted(
        {
            value
            for author in entry.get("authors", [])
            if (value := clean_text(author.get("name"), 200))
        }
    )
    categories = sorted(
        {value for tag in entry.get("tags", []) if (value := clean_text(tag.get("term"), 100))}
    )
    return Article(
        id=article_id,
        title=title,
        url=url,
        source_feed_ids=(feed.id,),
        published_at=_rfc3339(effective) or "",
        authors=tuple(authors),
        categories=tuple(categories),
        guid=clean_text(entry.get("id"), 2048),
        summary=clean_text(entry.get("summary"), 10_000),
        published_raw=published_raw,
        updated_at=_rfc3339(updated),
        updated_raw=updated_raw,
        language=entry.get("language") or feed.language,
    )


def deduplicate(articles: Iterable[Article]) -> tuple[list[Article], int]:
    grouped: dict[str, list[Article]] = {}
    for article in articles:
        grouped.setdefault(article.id, []).append(article)
    merged: list[Article] = []
    for candidates in grouped.values():
        candidates.sort(key=lambda item: (item.source_feed_ids[0], item.title, item.url))
        first = candidates[0]
        sources = tuple(sorted({feed for item in candidates for feed in item.source_feed_ids}))
        merged.append(
            Article(
                **{
                    **first.__dict__,
                    "source_feed_ids": sources,
                    "authors": tuple(sorted({x for item in candidates for x in item.authors})),
                    "categories": tuple(
                        sorted({x for item in candidates for x in item.categories})
                    ),
                }
            )
        )
    # Stable sorts express the contract exactly: published_at DESC, id ASC.
    merged.sort(key=lambda item: item.id)
    merged.sort(key=lambda item: item.published_at, reverse=True)
    return merged, sum(len(items) - 1 for items in grouped.values())

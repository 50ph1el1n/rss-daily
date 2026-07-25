import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .models import SCHEMA_VERSION, Feed

FEED_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
TAG = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")


def _http_url(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme.lower() in {"http", "https"} and bool(parts.netloc)


def load_registry(path: Path) -> tuple[list[Feed], int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("feeds"), list):
        raise ValueError("CONFIG_SCHEMA_INVALID")

    feeds: list[Feed] = []
    ids: set[str] = set()
    urls: set[str] = set()
    for raw in data["feeds"]:
        feed_id = raw.get("id", "")
        url = raw.get("url", "")
        title = raw.get("title", "")
        tags = raw.get("tags", [])
        if (
            raw.get("schema_version") != SCHEMA_VERSION
            or not FEED_ID.fullmatch(feed_id)
            or feed_id in ids
            or not isinstance(title, str)
            or not title.strip()
            or not _http_url(url)
            or url in urls
            or not isinstance(raw.get("enabled"), bool)
            or not isinstance(tags, list)
            or any(not isinstance(tag, str) or not TAG.fullmatch(tag) for tag in tags)
        ):
            raise ValueError(f"CONFIG_FEED_INVALID:{feed_id or '<missing>'}")
        ids.add(feed_id)
        urls.add(url)
        feeds.append(
            Feed(
                id=feed_id,
                title=title.strip(),
                url=url,
                enabled=raw["enabled"],
                tags=tuple(sorted(set(tags))),
                homepage_url=raw.get("homepage_url"),
                language=raw.get("language"),
                notes=raw.get("notes"),
            )
        )
    feeds.sort(key=lambda item: item.id)
    return feeds, sum(not feed.enabled for feed in feeds)

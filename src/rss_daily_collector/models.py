from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class Feed:
    id: str
    title: str
    url: str
    enabled: bool
    tags: tuple[str, ...]
    homepage_url: str | None = None
    language: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    url: str
    source_feed_ids: tuple[str, ...]
    published_at: str
    authors: tuple[str, ...]
    categories: tuple[str, ...]
    guid: str | None = None
    summary: str | None = None
    published_raw: str | None = None
    updated_at: str | None = None
    updated_raw: str | None = None
    language: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        data["source_feed_ids"] = list(self.source_feed_ids)
        data["authors"] = list(self.authors)
        data["categories"] = list(self.categories)
        return {"schema_version": data.pop("schema_version"), **data}

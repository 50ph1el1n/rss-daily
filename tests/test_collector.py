import json
from datetime import date
from pathlib import Path

from rss_daily_collector.export import publish_daily
from rss_daily_collector.models import SCHEMA_VERSION, Article
from rss_daily_collector.normalize import deduplicate, normalize_url
from rss_daily_collector.registry import load_registry


def article(feed_id: str) -> Article:
    return Article(
        id="sha256:" + "a" * 64,
        title="A title",
        url="https://example.com/post",
        source_feed_ids=(feed_id,),
        published_at="2026-07-25T00:00:00Z",
        authors=(),
        categories=(),
    )


def test_registry_and_url(tmp_path: Path) -> None:
    registry = tmp_path / "feeds.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "feeds": [
                    {
                        "schema_version": SCHEMA_VERSION,
                        "id": "example-feed",
                        "title": "Example",
                        "url": "https://EXAMPLE.com:443/feed#fragment",
                        "enabled": True,
                        "tags": ["tech"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    feeds, disabled = load_registry(registry)
    assert feeds[0].id == "example-feed"
    assert disabled == 0
    assert normalize_url(feeds[0].url) == "https://example.com/feed"


def test_deduplicate_is_deterministic() -> None:
    first, duplicates = deduplicate([article("z-feed"), article("a-feed")])
    second, _ = deduplicate([article("a-feed"), article("z-feed")])
    assert first == second
    assert first[0].source_feed_ids == ("a-feed", "z-feed")
    assert duplicates == 1


def test_order_is_published_desc_id_asc() -> None:
    later_b = Article(
        **{
            **article("example-feed").__dict__,
            "id": "sha256:" + "b" * 64,
            "published_at": "2026-07-25T01:00:00Z",
        }
    )
    later_a = Article(
        **{
            **later_b.__dict__,
            "id": "sha256:" + "a" * 64,
        }
    )
    earlier = Article(
        **{
            **later_b.__dict__,
            "id": "sha256:" + "c" * 64,
            "published_at": "2026-07-25T00:00:00Z",
        }
    )
    result, _ = deduplicate([earlier, later_b, later_a])
    assert [item.id[-1] for item in result] == ["a", "b", "c"]


def test_publish_daily(tmp_path: Path) -> None:
    target = date(2026, 7, 25)
    items = [article("example-feed")]
    digest = {
        "schema_version": SCHEMA_VERSION,
        "collection_date": target.isoformat(),
        "timezone": "Asia/Taipei",
        "article_count": 1,
        "articles": [items[0].to_dict()],
    }
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "run_id": "e5a0dd73-6199-413c-8787-0c93478098ef",
        "collection_date": target.isoformat(),
        "status": "success",
        "entry_counts": {"exported": 1},
    }
    health = {
        "schema_version": SCHEMA_VERSION,
        "run_id": metadata["run_id"],
        "collection_date": target.isoformat(),
        "feeds": [],
    }
    published = publish_daily(tmp_path, target, digest, metadata, health, items, False)
    assert (published / "articles.json").exists()
    assert (
        json.loads((tmp_path / "latest.json").read_text())["collection_date"] == target.isoformat()
    )

import logging
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import feedparser

from .export import publish_daily
from .fetch import FetchFailure, fetch
from .models import SCHEMA_VERSION, Article
from .normalize import TAIPEI, article_from_entry, deduplicate
from .registry import load_registry


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def collect(
    registry_path: Path,
    data_root: Path,
    collection_date: date | None,
    dry_run: bool,
    overwrite: bool,
    trigger: str,
    logger: logging.Logger,
) -> int:
    started = utc_now()
    run_id = str(uuid.uuid4())
    target_date = collection_date or started.astimezone(TAIPEI).date()
    feeds, disabled = load_registry(registry_path)
    enabled = [feed for feed in feeds if feed.enabled]
    if not enabled:
        raise ValueError("CONFIG_NO_ENABLED_FEEDS")
    logger.info("Collection started.", extra={"event": "run_started", "run_id": run_id})

    candidates: list[Article] = []
    health: list[dict[str, Any]] = []
    seen = selected = invalid = 0
    succeeded = failed = 0
    for feed in enabled:
        feed_started = utc_now()
        try:
            response = fetch(feed.url)
            parsed = feedparser.parse(response.body)
            if parsed.bozo and not parsed.entries:
                raise ValueError("PARSE_MALFORMED_FEED")
            entries = list(parsed.entries)
            feed_articles = [
                article
                for entry in entries
                if (article := article_from_entry(entry, feed, target_date)) is not None
            ]
            candidates.extend(feed_articles)
            seen += len(entries)
            selected += len(feed_articles)
            invalid += len(entries) - len(feed_articles)
            succeeded += 1
            completed = utc_now()
            health.append(
                {
                    "feed_id": feed.id,
                    "status": "succeeded",
                    "started_at": _stamp(feed_started),
                    "completed_at": _stamp(completed),
                    "duration_ms": int((completed - feed_started).total_seconds() * 1000),
                    "attempts": response.attempts,
                    "entries_seen": len(entries),
                    "entries_selected": len(feed_articles),
                    "entries_exported": len(feed_articles),
                    "entries_skipped": len(entries) - len(feed_articles),
                    "warnings": ["PARSE_WARNING"] if parsed.bozo else [],
                    "http_status": response.status,
                    "final_url": response.final_url,
                    "content_type": response.content_type,
                    "etag": response.etag,
                    "last_modified": response.last_modified,
                    "error": None,
                }
            )
        except (FetchFailure, ValueError) as exc:
            failed += 1
            completed = utc_now()
            attempts = exc.attempts if isinstance(exc, FetchFailure) else 1
            status = exc.status if isinstance(exc, FetchFailure) else None
            code = exc.code if isinstance(exc, FetchFailure) else str(exc)
            health.append(
                {
                    "feed_id": feed.id,
                    "status": "failed",
                    "started_at": _stamp(feed_started),
                    "completed_at": _stamp(completed),
                    "duration_ms": int((completed - feed_started).total_seconds() * 1000),
                    "attempts": attempts,
                    "entries_seen": 0,
                    "entries_selected": 0,
                    "entries_exported": 0,
                    "entries_skipped": 0,
                    "warnings": [],
                    "http_status": status,
                    "final_url": None,
                    "content_type": None,
                    "etag": None,
                    "last_modified": None,
                    "error": {
                        "code": code,
                        "stage": "fetch" if isinstance(exc, FetchFailure) else "parse",
                        "message": code,
                        "retryable": isinstance(exc, FetchFailure)
                        and (status is None or status == 429 or status >= 500),
                    },
                }
            )
            logger.error(code, extra={"event": "feed_failed", "run_id": run_id, "feed_id": feed.id})

    if not succeeded:
        logger.error("All feeds failed.", extra={"event": "run_failed", "run_id": run_id})
        return 20
    articles, duplicate = deduplicate(candidates)
    completed = utc_now()
    status = "partial" if failed else "success"
    digest = {
        "schema_version": SCHEMA_VERSION,
        "collection_date": target_date.isoformat(),
        "timezone": "Asia/Taipei",
        "article_count": len(articles),
        "articles": [article.to_dict() for article in articles],
    }
    relative = f"data/{target_date:%Y/%m/%d}"
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "collection_date": target_date.isoformat(),
        "timezone": "Asia/Taipei",
        "started_at": _stamp(started),
        "completed_at": _stamp(completed),
        "duration_ms": int((completed - started).total_seconds() * 1000),
        "status": status,
        "trigger": trigger,
        "feed_counts": {
            "configured": len(feeds),
            "enabled": len(enabled),
            "disabled": disabled,
            "succeeded": succeeded,
            "failed": failed,
        },
        "entry_counts": {
            "seen": seen,
            "selected": selected,
            "exported": len(articles),
            "duplicate": duplicate,
            "skipped_invalid_date": invalid,
            "skipped_invalid_entry": 0,
        },
        "artifacts": {
            "markdown": f"{relative}/README.md",
            "digest": f"{relative}/articles.json",
            "metadata": f"{relative}/metadata.json",
            "feed_health": f"{relative}/feed_health.json",
        },
        "github_run_id": None,
        "commit_sha_before": None,
        "collector_version": "1.0.0",
    }
    health_document = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "collection_date": target_date.isoformat(),
        "feeds": sorted(health, key=lambda item: item["feed_id"]),
    }
    if dry_run:
        logger.info(
            f"Dry run complete: {len(articles)} articles.",
            extra={"event": "run_completed", "run_id": run_id},
        )
    else:
        publish_daily(
            data_root, target_date, digest, metadata, health_document, articles, overwrite
        )
        logger.info(
            f"Published {len(articles)} articles.",
            extra={"event": "run_completed", "run_id": run_id},
        )
    return 2 if status == "partial" else 0

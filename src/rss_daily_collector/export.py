import json
import shutil
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from .models import SCHEMA_VERSION, Article


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def daily_path(data_root: Path, collection_date: date) -> Path:
    return data_root / f"{collection_date:%Y}" / f"{collection_date:%m}" / f"{collection_date:%d}"


def render_markdown(collection_date: date, articles: list[Article]) -> str:
    lines = [f"# RSS Daily — {collection_date.isoformat()}", "", f"共 {len(articles)} 篇文章。", ""]
    for article in articles:
        safe_title = article.title.replace("[", "\\[").replace("]", "\\]")
        lines.extend(
            [
                f"## [{safe_title}]({article.url})",
                "",
                f"- Article ID：`{article.id}`",
                f"- Source：{', '.join(article.source_feed_ids)}",
                f"- Published：{article.published_at}",
            ]
        )
        if article.authors:
            lines.append(f"- Authors：{', '.join(article.authors)}")
        if article.summary:
            lines.extend(["", article.summary])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _validate_daily(path: Path, collection_date: date) -> None:
    required = {"README.md", "articles.json", "metadata.json", "feed_health.json"}
    if {item.name for item in path.iterdir()} != required:
        raise ValueError("EXPORT_ARTIFACT_SET_INVALID")
    digest = json.loads((path / "articles.json").read_text(encoding="utf-8"))
    metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
    health = json.loads((path / "feed_health.json").read_text(encoding="utf-8"))
    expected = collection_date.isoformat()
    if (
        digest.get("collection_date") != expected
        or metadata.get("collection_date") != expected
        or health.get("collection_date") != expected
        or digest.get("article_count") != len(digest.get("articles", []))
        or metadata.get("entry_counts", {}).get("exported") != digest.get("article_count")
        or metadata.get("run_id") != health.get("run_id")
    ):
        raise ValueError("EXPORT_CROSS_FILE_INVALID")


def publish_daily(
    data_root: Path,
    collection_date: date,
    digest: dict[str, Any],
    metadata: dict[str, Any],
    health: dict[str, Any],
    articles: list[Article],
    overwrite: bool,
) -> Path:
    destination = daily_path(data_root, collection_date)
    if destination.exists() and not overwrite:
        raise FileExistsError("ARCHIVE_DATE_EXISTS")
    data_root.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=data_root))
    try:
        write_json(temp / "articles.json", digest)
        write_json(temp / "metadata.json", metadata)
        write_json(temp / "feed_health.json", health)
        (temp / "README.md").write_text(
            render_markdown(collection_date, articles), encoding="utf-8", newline="\n"
        )
        _validate_daily(temp, collection_date)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            backup = destination.with_name(destination.name + ".backup")
            if backup.exists():
                shutil.rmtree(backup)
            destination.replace(backup)
            try:
                temp.replace(destination)
            except Exception:
                backup.replace(destination)
                raise
            shutil.rmtree(backup)
        else:
            temp.replace(destination)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    rebuild_indexes(data_root)
    return destination


def scan_days(data_root: Path) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    for metadata_path in data_root.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/metadata.json"):
        folder = metadata_path.parent
        digest_path = folder / "articles.json"
        if not digest_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
        relative = folder.relative_to(data_root).as_posix()
        days.append(
            {
                "collection_date": metadata["collection_date"],
                "status": metadata["status"],
                "article_count": digest["article_count"],
                "digest_path": f"data/{relative}/articles.json",
                "metadata_path": f"data/{relative}/metadata.json",
                "markdown_path": f"data/{relative}/README.md",
                "feed_health_path": f"data/{relative}/feed_health.json",
            }
        )
    return sorted(days, key=lambda item: item["collection_date"], reverse=True)


def rebuild_indexes(data_root: Path) -> None:
    data_root.mkdir(parents=True, exist_ok=True)
    days = scan_days(data_root)
    write_json(
        data_root / "index.json",
        {
            "schema_version": SCHEMA_VERSION,
            "day_count": len(days),
            "days": [
                {
                    key: day[key]
                    for key in (
                        "collection_date",
                        "status",
                        "article_count",
                        "digest_path",
                        "metadata_path",
                    )
                }
                for day in days
            ],
        },
    )
    years: list[dict[str, Any]] = []
    for year in sorted({day["collection_date"][:4] for day in days}, reverse=True):
        year_days = [day for day in days if day["collection_date"].startswith(year)]
        months = []
        for month in sorted({day["collection_date"][5:7] for day in year_days}, reverse=True):
            month_days = [day for day in year_days if day["collection_date"][5:7] == month]
            months.append(
                {
                    "month": month,
                    "day_count": len(month_days),
                    "article_count": sum(day["article_count"] for day in month_days),
                    "days": [
                        {
                            key: day[key]
                            for key in (
                                "collection_date",
                                "status",
                                "article_count",
                                "digest_path",
                                "markdown_path",
                            )
                        }
                        for day in month_days
                    ],
                }
            )
        years.append(
            {
                "year": year,
                "day_count": len(year_days),
                "article_count": sum(day["article_count"] for day in year_days),
                "months": months,
            }
        )
    write_json(
        data_root / "archive.json",
        {
            "schema_version": SCHEMA_VERSION,
            "total_days": len(days),
            "total_articles": sum(day["article_count"] for day in days),
            "years": years,
        },
    )
    latest = data_root / "latest.json"
    if days:
        day = days[0]
        write_json(
            latest,
            {
                "schema_version": SCHEMA_VERSION,
                **{
                    key: day[key]
                    for key in (
                        "collection_date",
                        "status",
                        "article_count",
                        "digest_path",
                        "markdown_path",
                        "metadata_path",
                        "feed_health_path",
                    )
                },
            },
        )
    elif latest.exists():
        latest.unlink()


def validate_archive(data_root: Path) -> int:
    if not data_root.exists():
        return 0
    for day in scan_days(data_root):
        collection_date = date.fromisoformat(day["collection_date"])
        _validate_daily(daily_path(data_root, collection_date), collection_date)
    return len(scan_days(data_root))

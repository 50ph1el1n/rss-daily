import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .collect import collect
from .export import rebuild_indexes, validate_archive
from .logging_config import configure_logging
from .registry import load_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rss-daily", description="Collect → Normalize → Export")
    parser.add_argument("--registry", type=Path, default=Path("config/feeds.json"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    sub = parser.add_subparsers(dest="command", required=True)
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--date", type=date.fromisoformat)
    collect_parser.add_argument("--dry-run", action="store_true")
    collect_parser.add_argument("--overwrite", action="store_true")
    sub.add_parser("validate")
    sub.add_parser("rebuild-index")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            feeds, _ = load_registry(args.registry)
            validate_archive(args.data_root)
            if not any(feed.enabled for feed in feeds):
                raise ValueError("CONFIG_NO_ENABLED_FEEDS")
            return 0
        if args.command == "rebuild-index":
            rebuild_indexes(args.data_root)
            return 0
        return collect(
            registry_path=args.registry,
            data_root=args.data_root,
            collection_date=args.date,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            trigger="local",
            logger=configure_logging(),
        )
    except FileExistsError as exc:
        print(str(exc))
        return 10
    except (OSError, ValueError) as exc:
        print(str(exc))
        return 10

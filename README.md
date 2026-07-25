# RSS Daily Collector

RSS Daily Collector 是 Knowledge Pipeline 的 Collection Layer，只負責：

```text
Collect → Normalize → Export
```

每天台北時間 07:30 由 GitHub Actions 收集 RSS/Atom Feed，輸出 Markdown、JSON、
Metadata、FeedHealth 與 indexes，然後 commit 回 repository。

## Quick Start

```bash
python -m pip install -e ".[dev]"
python -m rss_daily_collector validate
python -m rss_daily_collector collect --dry-run
python -m pytest
```

編輯 [`config/feeds.json`](config/feeds.json) 加入來源。完整產品與工程規格請從
[`docs/README.md`](docs/README.md) 開始閱讀。

## Commands

```bash
python -m rss_daily_collector collect [--date YYYY-MM-DD] [--dry-run] [--overwrite]
python -m rss_daily_collector validate
python -m rss_daily_collector rebuild-index
```

GitHub 上可從 **Actions → Daily Collect → Run workflow** 手動執行；排程為每日
`23:30 UTC`，即台北時間 `07:30`。

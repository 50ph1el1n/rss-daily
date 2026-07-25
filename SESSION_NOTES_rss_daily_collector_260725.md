# SESSION_NOTES_rss_daily_collector_260725

---
## 2026-07-25 13:52

## 背景與目標

建立 RSS Daily Collector，作為 Knowledge Pipeline 的 Collection Layer。系統只負責
`Collect → Normalize → Export`，每天台北時間 07:30 由 GitHub Actions 收集 RSS/Atom
Feed，輸出 Markdown、JSON、Metadata、FeedHealth、Latest、Index 與 Archive，再 commit
回 GitHub。AI 摘要、推薦、Embedding、Vector Database、Knowledge Graph、Obsidian 與
Web UI 均不在範圍內。

Repository：

- GitHub：`https://github.com/50ph1el1n/rss-daily`
- 本機：`C:\Users\LZT\OneDrive\Desktop\SF\rss-daily`

## 對話摘要

- **Q**: 先以 Documentation First Development 建立可長期維護的企業級產品規格。
  **A**: 已建立 `docs/` 七份 SSOT 文件，包含 56 項 FR、32 項 AC、Schema、架構、ADR、
  Sprint 與貢獻規範。
- **Q**: 完成安裝、Collector MVP 與 GitHub Actions。
  **A**: 已實作 Python Collector、deterministic normalization/export、tests 與每日 workflow。
- **Q**: 加入 16 個 RSS 並啟動每日收集。
  **A**: 16 個來源皆加入 registry；本機 dry-run 為 16/16 成功、39 篇。
- **Q**: 處理 Substack 在 GitHub Actions 的 HTTP 403。
  **A**: Ubuntu 與 macOS hosted runner 都只有 6/16 成功；10 個 Substack 全部 403。
  browser-compatible headers diagnostic 亦為 10/10 403，確認不是 header 問題。
- **Q**: 暫時不要收集 Substack。
  **A**: 本次變更將 10 個 Substack Feed 設為 `enabled: false`，保留設定與停用原因。

## 已完成事項

- 建立並合併 Documentation First 規格。
- 實作 Python package、Feed registry、RSS/Atom parsing、台北日界線、UTC timestamps、
  stable Article ID、dedup、Markdown/JSON 雙輸出、Metadata、FeedHealth 與 indexes。
- 建立 `.github/workflows/daily-collect.yml`，支援 schedule 與 workflow_dispatch。
- 修正新建 `data/` 未被 `git diff` 偵測而無法 commit 的 workflow bug。
- 加入並驗證 16 個使用者指定 Feed。
- PR #1：加入 16 個 RSS。
- PR #2：runner 由 `ubuntu-latest` 改為 `macos-latest`。
- PR #3：加入一次性 Substack header diagnostic。
- PR #4：移除已完成的 diagnostic workflow。
- Diagnostic run `30146399407`：Collector headers 與 browser-compatible headers 對 10 個
  Substack Feed 均為 HTTP 403。
- 最近一次 macOS Daily Collect run `30146132423` 成功完成 workflow，但 collection status
  為 `partial`：6 Feed 成功、10 Feed 失敗、38 篇文章。

## 關鍵決策與結論

- `docs/` 是 Product/Architecture/Schema 的 Single Source of Truth。
- 無 database、無 AI、無 Web UI；JSON 是 canonical，Markdown 是 deterministic projection。
- 每日 archive 預設 immutable；同日重建必須明確使用 overwrite。
- Git 操作由 workflow 負責，source/config 變更必須透過 Pull Request 合併。
- Substack 403 與 parser、User-Agent、Accept-Language 無關；GitHub hosted runner 的網路來源
  被 Substack 阻擋。
- 暫不導入 public proxy 或 self-hosted runner；10 個 Substack Feed 改為 disabled。

## 目前狀態

- Production runner：`macos-latest`。
- Registry：16 個 Feed，其中 6 個 enabled、10 個 Substack disabled。
- Enabled：
  - BlockTempo
  - 中央社科技
  - FOMO SOC
  - Hacker News Frontpage
  - INSIDE
  - 科技新報 TechNews
- 排程：UTC `30 23 * * *`，即台北時間每日 07:30。
- 最近發布日期：`2026-07-25`。
- 本次 branch：`config/disable-substack-feeds`。

## 未完成 / 待處理

- 將本次停用 Substack 與 session notes 透過 PR 合併。
- 合併後可選擇手動 overwrite 今日 archive，讓 Metadata 顯示 6 enabled、0 failed；
  若不 overwrite，下一次排程會自然採用新設定。
- 未來若要恢復 Substack，需選擇受控 fetch proxy 或安全隔離的 self-hosted runner，並先新增
  ADR、安全評估與 acceptance tests。
- Sprint 4 hardening、benchmark、14 日 observation 尚未完成。

## 下次繼續的起點

1. 確認 `config/feeds.json` 中 10 個 Substack Feed 為 `enabled: false`。
2. 執行：

   ```powershell
   python -m rss_daily_collector validate
   python -m rss_daily_collector collect --dry-run
   ```

3. 檢查 dry-run 應為 6 個 enabled Feed，且不再出現 Substack HTTP 403。
4. 若要恢復 Substack，先評估 proxy/self-hosted runner，不要再嘗試 User-Agent workaround。

## 相關檔案與資源

- `config/feeds.json`
- `.github/workflows/daily-collect.yml`
- `docs/PRODUCT_REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/JSON_SCHEMA.md`
- `docs/DECISIONS.md`
- `docs/TODO.md`
- `data/latest.json`
- `data/2026/07/25/feed_health.json`
- PR #1：`https://github.com/50ph1el1n/rss-daily/pull/1`
- PR #2：`https://github.com/50ph1el1n/rss-daily/pull/2`
- PR #3：`https://github.com/50ph1el1n/rss-daily/pull/3`
- PR #4：`https://github.com/50ph1el1n/rss-daily/pull/4`
- Diagnostic run：`https://github.com/50ph1el1n/rss-daily/actions/runs/30146399407`

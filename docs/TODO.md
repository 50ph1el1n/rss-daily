# Delivery Plan

> 本文件是 implementation backlog 的 SSOT。未列入 Sprint 的項目不應暗中實作。  
> 狀態標記：`[ ]` 未開始、`[~]` 進行中、`[x]` 完成。

## Global Delivery Rules

- 每個 Sprint 先更新相關文件，再提交 implementation PR。
- 所有 acceptance 必須可由自動化 test、artifact inspection 或 workflow run 證明。
- 不以 future roadmap 作為 MVP dependency。
- 每一 Sprint 結束時執行 cross-document consistency check。
- branch 合併必須透過 Pull Request；禁止直接在本機 merge 到 default branch。

## Sprint 1 — Foundation and Contract

### Goal

建立最小可執行骨架、資料模型、設定契約與 deterministic normalization；尚不建立 production schedule。

### Tasks

- [x] 初始化 Git repository、Python 3.11 production `pyproject.toml` 與 root README。
- [x] 建立 `src/rss_daily_collector/` 與 CLI。
- [x] 以 frozen `dataclass` 定義核心 Feed 與 Article domain model。
- [x] 建立 `config/feeds.json` 與 validation。
- [x] 固定 Feed parser dependency `feedparser==6.0.11`。
- [x] 透過 feedparser adapter 支援 RSS 2.0、RSS 1.0 與 Atom。
- [x] 實作 timezone/date window、text、URL 與 timestamp normalization。
- [x] 實作 Article ID、dedup deterministic merge 與 stable sorting。
- [x] 建立 Ruff、Black、pytest 基線。
- [x] 建立 normalization、dedup 與 export unit tests。
- [ ] 將正式 machine-readable JSON Schema files 由本文件轉錄至 repository（若 validator 需要）。

### Definition of Done

- `python -m rss_daily_collector --help` 可執行。
- registry validation 與純 domain tests 全數通過。
- 三種 Feed fixtures 可轉為 neutral records。
- 相同/亂序 fixtures 產生完全相同 Article list。
- 無 network call 的 test suite 可在乾淨環境重現。

### Acceptance

- AC-001、AC-002、AC-003、AC-004、AC-006、AC-010、AC-011、AC-012、AC-014、AC-021。

## Sprint 2 — MVP: End-to-End Collection and Export

### Goal

完成可由本機執行的 `Collect → Normalize → Export` MVP，包含 daily artifacts、partial success 與 atomic publish。

### Tasks

- [x] 實作 bounded HTTP fetch：User-Agent、timeout、redirect、response size。
- [x] 實作 429/5xx/timeout 有限 retry 與 permanent failure policy。
- [x] 實作 collection orchestration 與 per-feed isolation。
- [x] 實作 `collect --date/--dry-run/--overwrite`。
- [x] 實作 DailyDigest、Markdown、Metadata、FeedHealth exporters。
- [x] 實作 UTF-8/LF、stable JSON formatting 與 Markdown escaping。
- [x] 實作 temporary directory + validation + atomic replace。
- [x] 實作 `validate` command 與 cross-file invariants。
- [x] 實作 `rebuild-index`，產生 Index、Archive、Latest。
- [x] 實作 JSONL logging 與 stable error codes。
- [ ] 建立 end-to-end fixtures，覆蓋 success、partial、empty day、all failed。

### Definition of Done

- 本機可針對 fixtures 或測試 server 產生完整 `data/YYYY/MM/DD/`。
- JSON 與 Markdown article IDs/order 一致。
- all-feed failure 與 export validation failure 不留下 published partial files。
- overwrite 與 backfill 遵循 immutable archive/Latest 規則。
- CLI exit codes 與 Architecture 規格一致。

### Acceptance

- AC-005、AC-007、AC-008、AC-009、AC-013、AC-015、AC-016、AC-017、AC-022、AC-023、AC-024、AC-025、AC-026、AC-027、AC-028、AC-029。

## Sprint 3 — GitHub Actions Productionization

### Goal

將 MVP 安全部署為每日 07:30 Asia/Taipei 的 repository-native pipeline。

### Tasks

- [x] 建立 `.github/workflows/daily-collect.yml`。
- [x] 設定 UTC cron、workflow_dispatch inputs 與 concurrency group。
- [x] 設定 Python 3.11、dependency cache 與 pinned install。
- [x] 串接 validate → tests → collect → validate artifacts。
- [x] 正確處理 partial exit code 2。
- [x] 產生 GitHub Job Summary。
- [x] 無 diff 時 no-op；有 diff 時固定 bot identity/message commit。
- [x] push 前做 non-force rebase safety check；衝突時失敗。
- [x] 設定最小 `contents: write` 權限與 job timeout。
- [ ] 失敗時上傳經 redaction 的 diagnostics，retention 14 days。
- [ ] 建立 branch protection 與 PR checklist 文件/設定指引。
- [ ] 以 workflow_dispatch 完成 staging repository smoke test。

### Definition of Done

- 手動與 scheduled simulation 都能正確計算台北日期。
- 成功/partial 可 commit；failed 不 commit。
- no-op 不建立空 commit。
- workflow 不使用 secret 以外洩風險高的輸出，也不 force push。
- Job Summary 清楚列出 Feed 與 entry counts。

### Acceptance

- AC-018、AC-019、AC-020、AC-029、AC-032，以及 Product Requirements §14 全項。

## Sprint 4 — Hardening and Release 1.0

### Goal

完成效能、安全、相容性與維運驗證，發布可長期維護的 v1.0。

### Tasks

- [ ] 建立 100 Feeds/10,000 entries benchmark fixtures。
- [ ] 驗證 15 分鐘/512 MiB performance target。
- [ ] 進行 malformed XML、encoding、oversized response、redirect loop 測試。
- [ ] 進行 URL credential、log injection、HTML/script sanitization 測試。
- [ ] 驗證所有 schemas、examples 與 generated validators 一致。
- [ ] 建立 reader compatibility tests 與 unknown-field/unknown-major tests。
- [ ] 建立 disaster recovery runbook：補跑、修正 partial、push conflict。
- [ ] 建立 dependency update/security review 流程。
- [ ] 執行至少 14 個連續日的 observation run。
- [ ] 修復 observation 期間的 correctness/reliability 問題。
- [ ] 完成文件、CLI help、release notes 與 v1.0 tag。

### Definition of Done

- 所有 functional/non-functional acceptance 通過或有書面 waiver。
- 14 日執行無資料遺失；所有 partial/failed 均可從 log 說明。
- Schema v1 compatibility tests 通過。
- Maintainer 僅閱讀 `docs/` 可完成新增 Feed、手動補跑與故障處理。
- v1.0 release 由 PR 審查後建立。

### Acceptance

- AC-030、AC-031，以及 NFR-001 至 NFR-012 的證據清單完成。

## Deferred Backlog

以下不屬於 Sprint 1–4：

- Conditional GET state。
- 每日多次抓取。
- Raw Feed 永久保存。
- NDJSON 或其他 exporter。
- Database/object storage。
- Feed health trend dashboard。
- 任何 AI/Embedding/UI 功能。

新增 Deferred 項目不代表承諾；進入 Sprint 前必須有使用情境、acceptance 與必要 ADR。

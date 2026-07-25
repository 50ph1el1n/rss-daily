# RSS Daily Collector — Product Specification

> 文件狀態：Approved for Implementation  
> 規格版本：1.0.0  
> 最後更新：2026-07-25  
> 規範層級：本文件定義產品需求；資料契約以 `JSON_SCHEMA.md` 為準，技術結構以 `ARCHITECTURE.md` 為準。

## 1. Executive Summary

RSS Daily Collector 是 Knowledge Pipeline 的 Collection Layer。系統每天在台北時間 07:30 由 GitHub Actions 啟動，讀取設定中的 RSS 2.0、RSS 1.0 與 Atom Feed，擷取「台北日曆日的今日文章」，完成欄位正規化、去重、排序與檔案輸出，再將結果 commit 回 GitHub。

產品只負責 `Collect → Normalize → Export`。它不是 RSS Reader，也不執行摘要、推薦、分類、Embedding、Knowledge Graph 或任何 AI 推論。下游（例如 ChatGPT）只需讀取穩定、可追蹤、可重建的 Markdown、JSON、Metadata 與 Index。

成功標準不是功能數量，而是：每日資料可靠落地、同一輸入產生相同輸出、單一 Feed 故障不阻塞整批、格式可長期演進、維運者能從 Git history 與結構化 log 完整追查。

## 2. Project Background

RSS/Atom 是開放且低耦合的資訊來源，但不同發布者對時間、識別碼、HTML、編碼與欄位的實作不一致。若直接交由 AI 或人工閱讀，會重複支付抓取與清理成本，也難以判斷資料是否完整。

本專案將外部、易變的 Feed 轉換成 repository 內部、穩定的 daily dataset。GitHub 同時提供排程執行環境、版本控制、審查軌跡與低成本保存，符合第一階段無伺服器、無資料庫的需求。

## 3. Problem Statement

需要解決：

- 多來源 Feed 格式與欄位不一致。
- 發布時間可能缺失、含錯誤 timezone 或晚到。
- 同一文章可能有 GUID、URL 或標題的不同變體。
- 網路、解析或單一來源失敗可能讓整批資料不完整。
- AI 下游需要穩定 Schema，而不是直接面對不可信 XML。
- 每日輸出必須可重跑、可比對、可追溯，且不因執行順序產生 noisy diff。

若不建立 Collection Layer，下游會把抓取、清理與推論耦合，導致不可重現、難以測試且難以替換。

## 4. Vision

建立一個五年以上仍可理解、可重建、可擴充的 Feed collection foundation：來源設定清楚、資料契約穩定、執行結果透明，任何下游工具不需知道 RSS/Atom 的差異。

## 5. Goals

- 每日 07:30（Asia/Taipei）自動收集當日文章。
- 支援多個 RSS/Atom Feed，來源可由版本控制設定檔管理。
- 將來源資料正規化為一致的 Article 與 Feed 模型。
- 同時輸出人類可讀 Markdown 與機器可讀 JSON。
- 產出執行 Metadata、FeedHealth、每日 Index、Latest pointer 與 Archive index。
- 具備 deterministic ordering、stable identifiers 與 atomic write。
- 單一來源失敗時繼續處理其餘來源，並明確標示 partial success。
- 所有變更可由 Git commit 稽核，所有契約有版本。

## 6. Non-goals

- 不做 AI 摘要、翻譯、推薦、評分或主題分類。
- 不建立 Embedding、Vector Database、Knowledge Graph。
- 不整合 Obsidian 或其他筆記工具。
- 不提供 Web UI、行動 App、登入或多租戶。
- 不抓取文章全文、不繞過 paywall、不執行 browser automation。
- 不提供全文搜尋、已讀狀態、收藏、通知或電子報。
- 不使用 SQLite、PostgreSQL、MongoDB 或 cache server。
- 不追求即時收集；排程外的手動執行僅供維運。
- 不保證來源本身的正確性或永久可用。

## 7. Engineering Principles

1. **Documentation First Development**：先更新規格，再更新實作。
2. **Single Source of Truth**：需求、Schema、ADR 與工作清單只在 `docs/` 定義。
3. **Deterministic Design**：相同輸入與 collection date 必須產生 byte-stable domain outputs。
4. **Keep It Simple / YAGNI**：在實際需求出現前不導入 database、queue、plugin framework 或 distributed system。
5. **Standard Library First**：網路、時間、hash、JSON、logging 與檔案處理優先使用 Python standard library；Feed parser 是允許的單一核心第三方 runtime dependency。
6. **Clean Architecture**：domain model 不依賴 network、GitHub 或檔案系統。
7. **SOLID with restraint**：依責任切分模組，不為單一實作建立 speculative abstraction。
8. **Fail Soft, Report Hard**：來源可部分失敗，但不可靜默忽略。
9. **Immutable Archive**：已成功發布的歷史日期預設不可被排程覆寫。
10. **Security by Default**：Feed 內容視為不可信輸入；不執行 HTML、script 或外部命令。

## 8. User Stories

- 作為 Knowledge Worker，我要每天取得統一格式的文章集合，以便交由 ChatGPT 分析。
- 作為 Maintainer，我要只修改一個 Feed 設定檔即可新增或停用來源。
- 作為 Maintainer，我要從 GitHub Actions summary 看出成功、部分成功與失敗原因。
- 作為 Data Consumer，我要依 stable article ID 去重與引用。
- 作為 Data Consumer，我要知道 collection date、Schema version 與資料完整性。
- 作為 Maintainer，我要安全重跑同一日期並預覽差異。
- 作為 Contributor，我要透過測試與 PR 確認輸出契約未被意外破壞。
- 作為 Auditor，我要由 commit、run ID、source URL 與 timestamps 追溯每日結果。

## 9. Functional Requirements

### Collection

- **FR-001** 系統必須從版本控制的 Feed registry 讀取來源。
- **FR-002** Feed registry 必須支援 `id`、`title`、`url`、`enabled` 與選用 `tags`。
- **FR-003** `feed.id` 必須在 registry 內唯一且符合 `^[a-z0-9][a-z0-9-]{1,62}$`。
- **FR-004** 系統必須忽略 `enabled: false` 的來源，並在 Metadata 計數。
- **FR-005** 系統必須支援 RSS 2.0、RSS 1.0/RDF 與 Atom 1.0。
- **FR-006** 系統必須使用明確 User-Agent、connect/read timeout 與有限 redirect。
- **FR-007** 每個 Feed 必須獨立抓取；單一來源錯誤不得中止其他來源。
- **FR-008** 系統必須限制單一回應大小，超限視為來源錯誤。
- **FR-009** 系統必須拒絕非 HTTP/HTTPS Feed URL。
- **FR-010** 系統必須記錄最終 response URL、HTTP status、content type、ETag 與 Last-Modified（若存在）。
- **FR-011** 系統不得執行或渲染 Feed 內 HTML、JavaScript 或附件。
- **FR-012** 手動執行必須可指定 collection date，預設為 Asia/Taipei 的當日。

### Date selection and normalization

- **FR-013** 「今日」必須以 `Asia/Taipei` 的 `[00:00:00, 次日 00:00:00)` 定義。
- **FR-014** 系統必須將可解析時間轉為 UTC RFC 3339 字串。
- **FR-015** 原始時間字串必須保留於 `published_raw` 或 `updated_raw`。
- **FR-016** 日期選擇優先使用 published time，其次 updated time。
- **FR-017** 若 entry 無任何可解析日期，預設不得納入 DailyDigest，並在 FeedHealth 計數。
- **FR-018** 系統必須正規化標題的前後空白與連續 whitespace。
- **FR-019** 系統必須正規化 URL：移除 fragment、正規化 scheme/host 大小寫與 default port；不得擅自移除 query。
- **FR-020** description/summary 必須轉為安全純文字並正規化 whitespace。
- **FR-021** author、categories 與 tags 缺失時必須使用空值或空陣列，不得猜測。
- **FR-022** 未知來源欄位不得自動提升為正式 Schema 欄位。

### Identity, deduplication, ordering

- **FR-023** Article ID 必須是 deterministic，優先由 canonical URL、其次 GUID、最後由 feed ID + title + effective time 生成。
- **FR-024** Article ID 格式必須為 `sha256:` 加 64 位小寫十六進位。
- **FR-025** 同一批次中相同 Article ID 必須只輸出一次。
- **FR-026** 跨 Feed 重複文章必須保留一筆 Article，並在 `source_feed_ids` 列出全部來源。
- **FR-027** 去重衝突時必須採 deterministic merge policy，不得依抓取完成順序決定。
- **FR-028** Article 必須依 `published_at` 降冪、`id` 升冪排序；缺時間項目不得進入每日文章集合。
- **FR-029** Feed 與 FeedHealth 必須依 `feed_id` 升冪排序。
- **FR-030** JSON object key 與輸出換行規則必須固定。

### Export and archive

- **FR-031** 每日必須輸出 `articles.json`，符合 `DailyDigest` Schema。
- **FR-032** 每日必須輸出 `README.md`，內容與 `articles.json` 的 article set 一致。
- **FR-033** 每日必須輸出 `metadata.json`，符合 Metadata Schema。
- **FR-034** 每日必須輸出 `feed_health.json`，包含每個啟用 Feed 的結果。
- **FR-035** 系統必須維護 `data/index.json`，列出所有成功發布日期。
- **FR-036** 系統必須維護 `data/latest.json`，指向最近成功或部分成功的 digest。
- **FR-037** 系統必須維護 `data/archive.json`，提供年度/月度彙總與檔案相對路徑。
- **FR-038** 空日（零篇文章但至少一個 Feed 成功）仍必須輸出有效 daily artifacts。
- **FR-039** 所有輸出必須先寫入暫存目錄、驗證後再 atomic replace。
- **FR-040** 任一必要 artifact 驗證失敗時，不得發布不完整日期目錄。
- **FR-041** 排程不得覆寫既有成功日期；手動 backfill 必須顯式使用 overwrite 選項。
- **FR-042** overwrite 前必須完成完整重建，不允許增量修改單篇文章。
- **FR-043** Markdown 必須 escape 會破壞結構的來源文字，且不得內嵌不可信 HTML。
- **FR-044** 所有 JSON 文件必須包含自己的 `schema_version`。

### Operation and observability

- **FR-045** CLI 必須支援 `collect`、`validate` 與 `rebuild-index` 三個命令。
- **FR-046** `collect` 必須支援 `--date YYYY-MM-DD`、`--dry-run` 與 `--overwrite`。
- **FR-047** `validate` 必須驗證 registry 與既有 artifacts，不進行 network request。
- **FR-048** 每次執行必須產生唯一 `run_id`，格式為 UUID。
- **FR-049** 系統必須輸出 machine-readable JSON Lines log 至 stdout。
- **FR-050** 系統必須產生 GitHub Actions Job Summary。
- **FR-051** 執行結果必須分類為 `success`、`partial` 或 `failed`。
- **FR-052** 至少一個啟用 Feed 成功且 artifacts 有效時，可發布 `success` 或 `partial`。
- **FR-053** 所有啟用 Feed 失敗、registry 無效或 export 驗證失敗時，必須為 `failed` 且不得 commit。
- **FR-054** commit message 必須固定為 `data: collect YYYY-MM-DD`。
- **FR-055** 沒有檔案差異時 workflow 必須成功結束且不得建立空 commit。
- **FR-056** GitHub Actions 手動觸發必須接受 date、dry-run、overwrite inputs。

## 10. Non-functional Requirements

- **NFR-001 Reliability**：正常來源條件下，每月排程成功率 ≥ 99%。
- **NFR-002 Determinism**：固定的原始 fixtures、設定與日期必須產生相同 domain artifact bytes；`run_id`、執行時間與 duration 僅存在 Metadata/FeedHealth，不納入 Article ID。
- **NFR-003 Performance**：100 個 Feed、10,000 entries 的執行應在 GitHub Actions 15 分鐘內完成。
- **NFR-004 Resource**：單次執行記憶體目標低於 512 MiB，無常駐服務。
- **NFR-005 Portability**：支援 Python 3.11，Linux 為 production target；本機 Windows/macOS 可執行驗證。
- **NFR-006 Maintainability**：公開函式具 type hints；核心 domain logic 有單元測試。
- **NFR-007 Security**：最小 GitHub token 權限，只允許 workflow `contents: write`；禁止記錄 secret。
- **NFR-008 Privacy**：不蒐集使用者資料；僅保存 Feed 公開資料與執行技術資訊。
- **NFR-009 Compatibility**：Schema 採 Semantic Versioning；minor 版本只允許向後相容新增。
- **NFR-010 Accessibility**：Markdown 使用語意標題、清楚連結文字與不依賴顏色的狀態。
- **NFR-011 Testability**：network、clock 與 filesystem boundary 可替換為 deterministic fixtures。
- **NFR-012 Operability**：錯誤訊息包含 feed_id、stage、error_code 與可採取動作。

## 11. Output Specification

規範目錄：

```text
data/
├── latest.json
├── index.json
├── archive.json
└── 2026/
    └── 07/
        └── 25/
            ├── README.md
            ├── articles.json
            ├── metadata.json
            └── feed_health.json
```

輸出規則：

- encoding：UTF-8（無 BOM）。
- newline：LF；檔案結尾保留一個 newline。
- JSON：2 spaces indent、Unicode 不 ASCII escape、固定 key insertion order。
- 日期目錄：Asia/Taipei collection date，固定 `YYYY/MM/DD`。
- 所有 artifact 內路徑使用 repository-relative POSIX path。
- Markdown 文章按 JSON 相同順序列出，至少包含標題、來源、發布時間、canonical URL 與摘要（若有）。
- `articles.json` 是文章集合的 canonical representation；Markdown 是 projection，不得加入額外推論。
- `metadata.json` 記錄 run facts；`feed_health.json` 記錄 per-feed facts。
- `latest.json`、`index.json`、`archive.json` 只在 daily artifacts 驗證通過後更新。

完整欄位與 validation 見 `JSON_SCHEMA.md`。

## 12. Logging Strategy

採 structured logging：

- stdout 每行一個 JSON object，供 GitHub Actions 保存。
- level：`DEBUG`、`INFO`、`WARNING`、`ERROR`。
- 必要欄位：`timestamp`、`level`、`event`、`run_id`、`message`。
- Feed 事件增加：`feed_id`、`stage`、`duration_ms`、`attempt`、`error_code`。
- 事件名稱固定且可查詢，例如 `run_started`、`feed_fetch_succeeded`、`feed_parse_failed`、`export_validated`、`run_completed`。
- 不記錄完整 Feed body、article body、Authorization header、cookie 或 secret。
- URL query 可能含 credential 時必須 redact。
- GitHub Job Summary 顯示總數、成功/失敗 Feed、文章數、狀態與 artifact path，不取代 structured log。
- repository 不永久 commit runtime log；GitHub Actions retention 由 workflow 設定。

## 13. Error Handling

錯誤分層：

| 類別 | 範例 | 行為 |
|---|---|---|
| Configuration | registry 語法錯、ID 重複 | fail fast，不發布 |
| Fetch | timeout、DNS、HTTP 5xx | 每 Feed 有限重試，失敗後繼續 |
| Parse | malformed XML、未知格式 | 標記 Feed failed，繼續 |
| Entry | 日期錯、URL 無效 | 跳過該 entry，增加計數 |
| Normalize | 欄位超限、文字無法清理 | 跳過 entry 並記錄 error code |
| Export | I/O、Schema validation | 整批 failed，不發布 |
| Git | push conflict、權限不足 | workflow failed；已產生檔案由 run artifact 協助診斷 |

重試只用於可能暫時性的 fetch 錯誤（timeout、429、5xx），最多 3 次，採有上限 exponential backoff；4xx（429 除外）與 parse error 不重試。錯誤不得被 bare `except` 吞掉。

## 14. GitHub Actions Specification

- Workflow：`.github/workflows/daily-collect.yml`。
- Trigger：
  - `schedule`：`30 23 * * *`（UTC，對應台北次日 07:30；台北無 DST）。
  - `workflow_dispatch`：`date`、`dry_run`、`overwrite`。
- Concurrency：group `rss-daily-collector`，`cancel-in-progress: false`。
- Runner：`macos-latest`；用於避開 Substack 對 GitHub Azure shared egress IP 的 HTTP 403。
- Runtime：Python 3.11；以 lock/requirements 驗證後安裝。
- Permissions：預設 `contents: read`，collect job 僅提升至 `contents: write`。
- Steps：checkout → setup Python → install → validate config → test → collect → validate artifacts → render summary → detect diff → commit → pull/rebase safety check → push。
- Commit author：固定 bot identity；message 使用 FR-054。
- Retention：失敗時上傳暫存輸出與 log，建議 14 天；不得包含 secrets。
- Timeout：job 20 分鐘。
- 排程延遲由 GitHub 控制；collection date 必須由 Asia/Taipei clock 計算，不能直接使用 UTC date。
- push 衝突不得 force push；workflow 應失敗並保留診斷。

## 15. Acceptance Criteria

- **AC-001** Given 一個有效 RSS 2.0 fixture，When collect，Then 產出符合 Schema 的 Article。
- **AC-002** Given 一個有效 Atom fixture，Then published/updated 正確轉為 UTC。
- **AC-003** Given RSS 1.0 fixture，Then 可正常解析。
- **AC-004** Given 兩個 Feed 指向同一 canonical URL，Then 只輸出一篇且保留兩個 source feed IDs。
- **AC-005** Given 相同 fixture 與日期執行兩次，Then domain artifacts byte-for-byte 相同。
- **AC-006** Given Feed entries 順序不同，Then輸出排序與 bytes 不變。
- **AC-007** Given 一個 Feed timeout、另一個成功，Then狀態為 partial 且成功文章被發布。
- **AC-008** Given 所有 Feed 失敗，Then無日期目錄與 index 變更。
- **AC-009** Given 零篇今日文章但 Feed 成功，Then發布有效空 digest。
- **AC-010** Given entry 無有效日期，Then不納入文章且 FeedHealth 計數增加。
- **AC-011** Given URL 含 fragment，Then canonical URL 不含 fragment。
- **AC-012** Given title 含多重 whitespace，Then標題被穩定正規化。
- **AC-013** Given 不可信 HTML summary，Then Markdown 不執行或保留 script/HTML。
- **AC-014** Given invalid registry，Then validate 非零結束且無 network request。
- **AC-015** Given 既有成功日期且無 overwrite，Then collect 拒絕覆寫。
- **AC-016** Given手動 overwrite，Then完整 artifacts 原子替換且 index 一致。
- **AC-017** Given Schema validation failure，Then不得發布任何部分檔案。
- **AC-018** Given無 Git diff，Then workflow 不建立 commit 且成功。
- **AC-019** Given有有效輸出，Then commit message 精確符合規格。
- **AC-020** Given scheduled run，Then collection date 依 Asia/Taipei 判定。
- **AC-021** Given Feed URL 是 file/ftp scheme，Then registry validation 失敗。
- **AC-022** Given response 超過大小限制，Then該 Feed 失敗且其他 Feed 繼續。
- **AC-023** Given 429/5xx，Then在上限內重試並記錄 attempt。
- **AC-024** Given 404，Then不重試並記錄 stable error code。
- **AC-025** Given artifacts，Then所有 JSON 皆有 schema_version 且使用 UTF-8/LF。
- **AC-026** Given每日成功，Then latest 指向該日，index/archive 包含該日。
- **AC-027** Given較舊日期 backfill，Then latest 仍指向時間上最新的有效日期。
- **AC-028** Given structured log，Then每行可獨立解析為 JSON 且無 secret。
- **AC-029** Given partial run，Then Metadata 與 Job Summary 都列出失敗 Feed。
- **AC-030** Given PR 修改 Schema major version，Then migration/compatibility note 存在。
- **AC-031** Given 100 Feeds/10,000 entries fixture，Then在 15 分鐘與 512 MiB 目標內完成。
- **AC-032** Given production workflow，Then僅具完成任務所需最小權限且不 force push。

## 16. Future Roadmap

Roadmap 僅表示可能方向，不構成當前承諾：

- Conditional GET（ETag/Last-Modified）狀態保存，以降低頻寬。
- 來源品質趨勢與長期健康報告。
- 多次每日收集與可設定 collection window。
- Content-addressed raw snapshot（僅在除錯與法遵需求成立時）。
- 其他 export adapter（例如 NDJSON），前提是有明確下游消費者。
- 獨立 storage backend 或 database，僅在 Git repository 規模或 concurrency 經量測超出限制後。

AI enrichment 永遠位於 Collection Layer 之外。

## 17. Known Limitations

- GitHub scheduled workflows 可能延遲，不保證精確 07:30 開始。
- Feed 可能只保留少量最新文章；每日單次抓取可能漏掉短生命週期項目。
- 發布者的錯誤時間可能造成文章落在錯誤日期；系統不猜測內容日期。
- URL normalization 不等同語意 canonicalization，無法辨識所有 tracking query。
- 無資料庫意味大型 archive 的 index rebuild 為 O(n) filesystem scan。
- Git history 會隨每日輸出成長；超出 repository 實務容量後才評估外部儲存。
- 只保存 Feed 提供的 summary，不抓取完整網頁內容。
- 排程執行依賴 GitHub Actions、網路與來源伺服器可用性。

## 18. Glossary

| 名詞 | 定義 |
|---|---|
| Article | 正規化後的單篇 Feed entry。 |
| Feed | registry 中的一個 RSS/Atom 來源及其描述。 |
| DailyDigest | 某個 Asia/Taipei 日曆日的 Article 集合。 |
| Collection Date | 決定「今日文章」範圍與 archive 路徑的台北日期。 |
| Effective Time | 用於日期選擇的 published time，缺失時為 updated time。 |
| Canonical URL | 經本系統保守正規化後的文章 URL。 |
| FeedHealth | 單次執行中某個 Feed 的抓取、解析與 entry 統計。 |
| Metadata | 單次 daily export 的執行與完整性資訊。 |
| Latest | 指向時間上最近有效 DailyDigest 的小型文件。 |
| Index | 所有有效日期的扁平清單。 |
| Archive | 依年/月聚合的 discovery 文件。 |
| Partial Success | 至少一個 Feed 成功、至少一個 Feed 失敗，且 artifacts 有效。 |
| Deterministic | 相同有效輸入、設定與日期產生相同 domain outputs。 |
| SSOT | Single Source of Truth，本專案即 `docs/` 與受其約束的 versioned artifacts。 |

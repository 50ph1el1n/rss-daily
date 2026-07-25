# Architecture Decision Records

> 狀態詞彙：Proposed、Accepted、Superseded、Deprecated。  
> ADR 一經 Accepted 不直接改寫決策；新決策以新的 ADR supersede 舊紀錄。文字勘誤可修正，但不得改變歷史意義。

## ADR-001：不使用 SQLite

- **Status**：Accepted
- **Date**：2026-07-25

### Context

系統是每日單一批次、append-oriented archive，資料由 Git 管理且主要 consumer 讀取檔案。SQLite 會引入 binary diff、migration、locking、backup 與 export 同步問題。

### Decision

不使用 SQLite。每日資料直接以 versioned JSON/Markdown 保存。

### Consequences

- 正面：Git diff 可讀、無 migration/runtime service、部署簡單。
- 負面：跨日查詢需讀 index/files；大量歷史資料掃描效率較低。
- Revisit trigger：repository 大小、查詢延遲或 concurrent writer 經量測無法接受。

### Alternatives

- SQLite：單檔易部署，但不適合 Git review 與每日 artifact SSOT。
- PostgreSQL：能力過剩且需要常駐服務。
- DuckDB：分析方便，但 Collection Layer 不負責分析。

## ADR-002：Markdown + JSON 雙輸出

- **Status**：Accepted
- **Date**：2026-07-25

### Context

人類與 ChatGPT 可直接閱讀 Markdown；自動化 consumer 需要嚴格 Schema。只選一種會讓另一類 consumer 承擔轉換成本。

### Decision

DailyDigest 以 JSON 為 canonical representation，Markdown 是 deterministic projection。

### Consequences

- 正面：兼顧可讀性與機器契約。
- 負面：必須驗證兩者 article set/order 一致。
- Markdown 不得加入 JSON 中不存在的推論或 enrichment。

### Alternatives

- JSON only：對人工 review 不友善。
- Markdown only：解析脆弱、Schema 不明確。
- HTML：不符合 repository-first 與安全純文字原則。

## ADR-003：使用 GitHub Actions 排程

- **Status**：Accepted
- **Date**：2026-07-25

### Context

需要每日排程、版本控制與低維運成本，且不需要常駐服務。

### Decision

使用 GitHub Actions，cron 為 `30 23 * * *` UTC，程式以 `Asia/Taipei` clock 決定 collection date。

### Consequences

- 正面：零 server 維運，與 repository/commit workflow 整合。
- 負面：排程可能延遲；受 runner、quota 與平台可用性影響。
- 提供 workflow_dispatch 作為補跑途徑。

### Alternatives

- Self-hosted cron：時間較可控，但增加主機與安全維運。
- Cloud Scheduler + Function：可行但引入 cloud resource 與 credential。

## ADR-004：No Database

- **Status**：Accepted
- **Date**：2026-07-25

### Context

資料天然依 collection date 分區，沒有 transaction-heavy query 或多 writer。

### Decision

repository filesystem + Git history 是 v1 唯一 persistence mechanism。

### Consequences

- 正面：資料可攜、可稽核、可由靜態工具消費。
- 負面：Git repository 會成長，index rebuild 是 O(n)。
- 不預建 storage abstraction；需求成立時以 ADR 新增。

### Alternatives

- Object storage：適合大量資料，但目前增加部署與 discovery 成本。
- Database：見 ADR-001，現階段不需要。

## ADR-005：Deterministic Output

- **Status**：Accepted
- **Date**：2026-07-25

### Context

並行 fetch、Feed entry 順序與 runtime metadata 容易造成無意義 diff，妨礙審查與重跑。

### Decision

固定 normalization、identity、merge、sort、JSON key、UTF-8/LF 與 Markdown projection。Runtime facts 隔離於 Metadata/FeedHealth。

### Consequences

- 正面：fixtures 可重現、diff 精簡、重跑可驗證。
- 負面：每個集合與衝突規則都必須明確；Schema 變更需謹慎。

### Alternatives

- 保留來源順序：簡單但不穩定。
- 依 fetch completion order：效能可能略好，但結果不可重現。

## ADR-006：UTC 儲存、Asia/Taipei 日界線

- **Status**：Accepted
- **Date**：2026-07-25

### Context

產品的「每天」以台北時間理解，但來源時間跨 timezone。

### Decision

選取範圍以 Asia/Taipei `[00:00, next 00:00)`；解析後 timestamps 一律輸出 UTC RFC 3339，同時保存 raw value。

### Consequences

- 正面：日界線符合產品語意，timestamps 可一致比較。
- 負面：來源缺 timezone 或時間錯誤時不可可靠修正；此類 entry 會被跳過。

### Alternatives

- 全 UTC date：會與使用者認知跨日。
- 保存各來源 local time：比較與排序不一致。

## ADR-007：不可變日封存與顯式覆寫

- **Status**：Accepted
- **Date**：2026-07-25

### Context

排程重跑若靜默覆寫歷史，可能改變已被下游引用的資料。

### Decision

排程不覆寫已成功發布日期。人工 backfill/rebuild 必須顯式 `--overwrite`，且採完整 atomic replacement。

### Consequences

- 正面：歷史穩定、意外重跑安全。
- 負面：修正來源或 normalization 後不會自動回寫歷史。

### Alternatives

- Upsert individual articles：會讓重建結果依歷史狀態，破壞 determinism。
- 永遠覆寫：操作簡單但風險高。

## ADR-008：單一 Feed 失敗採 Partial Success

- **Status**：Accepted
- **Date**：2026-07-25

### Context

外部 Feed 可用性不受本系統控制。要求全成功會讓健康來源資料因一個故障來源而整日缺失。

### Decision

至少一個 enabled Feed 成功即可發布；任一其他 Feed 失敗時標記 `partial`。全部失敗則不發布。

### Consequences

- 正面：最大化可用資料並清楚表達完整性。
- 負面：consumer 必須檢查 Metadata status；partial 不代表完整。

### Alternatives

- All-or-nothing：資料完整性概念簡單，但可用性過低。
- 靜默跳過：不可稽核，拒絕採用。

## ADR-009：保守 URL Normalization

- **Status**：Accepted
- **Date**：2026-07-25

### Context

URL 用於 identity，但任意刪除 query 可能改變資源語意；完全不正規化又會造成 fragment/default port 重複。

### Decision

只正規化 scheme/host case、移除 default port 與 fragment，保留 path/query 語意。不建立 tracking parameter list。

### Consequences

- 正面：低誤判、規則穩定。
- 負面：不同 tracking query 仍可能成為不同 Article。

### Alternatives

- 移除所有 query：可能合併不同內容。
- 來源特定 canonicalizer：維護成本高，未有需求。

## ADR-010：Feed Parser 為唯一核心 Runtime Dependency

- **Status**：Accepted
- **Date**：2026-07-25

### Context

RSS/Atom 的現實相容性與日期格式邊界繁多，自行實作 XML dialect parser 風險高；其餘能力 standard library 足夠。

### Decision

允許一個成熟、固定版本的 Feed parsing dependency；HTTP、hash、timezone、JSON、CLI、logging 與 filesystem 優先 standard library。具體套件在 Sprint 1 spike 後記錄版本。

### Consequences

- 正面：降低格式相容性風險，維持 dependency surface 小。
- 負面：需追蹤該套件安全與行為更新。

### Alternatives

- 純 standard library XML：依賴少，但需自行承擔大量不規範 Feed。
- 完整 scraping framework：功能與依賴過多。

## ADR-011：原子檔案發布，不做增量更新

- **Status**：Accepted
- **Date**：2026-07-25

### Context

四個 daily artifacts 與三個 global indexes 必須互相一致。中途 crash 不應留下半套資料。

### Decision

先在同 filesystem 的 temporary directory 完整寫入與驗證，再 atomic replace daily directory；最後由已驗證 archive rebuild global indexes。

### Consequences

- 正面：讀者不會看到半成品，overwrite 可安全回復。
- 負面：需要額外暫存空間；跨 filesystem rename 不支援。

### Alternatives

- 逐檔直接寫：簡單但會暴露 inconsistent state。
- Transactional database：違反 ADR-004。

## ADR-012：不保存完整 Raw Feed 或文章全文

- **Status**：Accepted
- **Date**：2026-07-25

### Context

Raw payload 有容量、版權、隱私與惡意內容風險；產品只需要正規化 Feed metadata。

### Decision

v1 不 commit raw XML、不抓取 article page、不保存全文。失敗診斷僅能在短期 workflow artifact 中保存經 redaction 的必要片段。

### Consequences

- 正面：repository 小、安全邊界清楚。
- 負面：來源變更後無法完整重播歷史 response。

### Alternatives

- 永久 raw snapshot：可重播但成本與風險顯著。
- 全文 crawler：超出 Collection Layer 範圍。

## ADR-013：Schema 使用 Semantic Versioning

- **Status**：Accepted
- **Date**：2026-07-25

### Context

下游需要知道何時可以安全忽略新欄位、何時必須 migration。

### Decision

所有 JSON artifact 自帶 Schema SemVer；minor 僅向後相容新增，breaking change 提升 major 並提供 migration ADR。

### Consequences

- 正面：consumer 可明確 dispatch 與 fail。
- 負面：欄位語意變更需版本治理，歷史可能有多個 major。

### Alternatives

- 無版本：短期簡單，長期不可安全演進。
- 日期版號：不能直接表達 compatibility。

## ADR-014：Git 操作由 Workflow 負責

- **Status**：Accepted
- **Date**：2026-07-25

### Context

Collector 的產品責任是 Collect/Normalize/Export。把 Git CLI 放進 application 會耦合環境與 credential。

### Decision

Python CLI 只產出/驗證檔案與 exit status；diff、commit、rebase safety check、push 由 GitHub Actions steps 執行，禁止 force push。

### Consequences

- 正面：本機測試簡單、權限邊界清楚、Collector 可離線 dry-run。
- 負面：workflow 需正確解讀 partial exit code 2。

### Alternatives

- Application 呼叫 Git：耦合且難測。
- GitHub API commit：額外 API 複雜度，無必要。

## ADR-015：GitHub Actions 使用 macOS Hosted Runner

- **Status**：Accepted
- **Date**：2026-07-25

### Context

16 個來源在本機可全部抓取，但 GitHub `ubuntu-latest` 上的 10 個 Substack Feed
一致回傳 HTTP 403；同一個 run 的 6 個非 Substack Feed 均成功。GitHub-hosted
Ubuntu runner 使用 Azure shared egress，來源端可能依 IP reputation 阻擋。

### Decision

production workflow 改用 `macos-latest`，以不同的 hosted runner 網路路徑進行
Substack 相容性測試與每日收集。

### Consequences

- 正面：維持無伺服器架構，只需一行 workflow 變更。
- 負面：不能保證來源端不封鎖 macOS runner；執行資源與 queue 行為可能不同。
- 若 macOS 仍回傳 403，必須新增 ADR 再評估受控 proxy 或安全隔離的 self-hosted
  runner，不得加入不透明公共 proxy。

### Alternatives

- 增加 403 retry：永久拒絕不會因 retry 解決，且會增加來源負擔。
- Self-hosted runner：網路可行，但 public repository 存在執行不受信任程式碼風險。
- Public proxy：可靠性、安全與資料治理不可接受。

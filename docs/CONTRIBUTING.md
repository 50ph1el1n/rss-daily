# Contributing Guide

感謝參與 RSS Daily Collector。本專案採 Documentation First Development：行為、資料契約或架構變更必須先更新 `docs/`，再更新程式與測試。

## 1. Development Environment

- Python：3.11（CI 與本機一致）。
- Production target：GitHub-hosted Ubuntu Linux。
- Formatter：Black。
- Linter：Ruff。
- Tests：pytest。
- Type hints：所有 public function、dataclass fields 與 module boundary 必須標註。
- Domain model：優先使用 frozen `dataclass`；不使用 dict 在核心層傳遞未驗證資料。
- Runtime dependencies：最少化並固定版本；新增前須說明 standard library 為何不足。

常用命令在 implementation 建立後應統一為：

```bash
python -m pip install -e ".[dev]"
ruff check .
black --check .
python -m pytest
python -m rss_daily_collector validate
```

實際 scripts 與 `pyproject.toml` 是命令實作來源；若命令變更，必須同步本文件與 root README。

## 2. Documentation First Workflow

1. 確認需求是否已存在於 `PRODUCT_REQUIREMENTS.md`。
2. 影響 JSON 欄位時先更新 `JSON_SCHEMA.md` 與 compatibility policy。
3. 影響系統邊界/不可逆選擇時新增 ADR，不覆寫舊 ADR。
4. 將工作加入 `TODO.md` 的 Sprint 或明確 backlog。
5. 才開始 implementation、tests 與 fixtures。
6. PR 內執行 consistency check。

純 bug fix 若只是讓實作回到既有規格，可不新增需求；PR 必須引用對應 FR/AC。

## 3. Coding Standards

### Python

- 遵循 PEP 8，由 Black/Ruff 自動執行可機械化規則。
- 使用 Python 3.11 syntax；避免為未支援版本加入 compatibility code。
- public API 必須有 type hints；不使用 `Any` 逃避 boundary validation。
- domain values 優先 immutable；不得以 global mutable state 保存 run data。
- small pure function 優先，I/O 保留在 infrastructure boundary。
- exception 必須具體；禁止 bare `except`、靜默吞錯與用 exception 控制正常流程。
- 使用 `pathlib`、`datetime/zoneinfo`、`hashlib`、`json`、`logging` 等 standard library。
- 不建立只有一個 implementation 的 interface、factory、service locator 或 dependency injection container。
- 不在 collector 引入 AI SDK、database driver、web framework 或 browser automation。

### Dataclass conventions

- Domain entity 使用 `@dataclass(frozen=True, slots=True)`，除非有明確理由。
- `list`/`dict` 不作為 mutable default；使用 immutable tuple 或 safe factory。
- parsing record 與 validated domain model 分開，避免半合法物件流入 exporter。
- validation failure 使用 stable error code，而非依賴 exception message。

### Logging

- 使用 structured JSONL event，不用 `print` 作 runtime logging（CLI help/output 除外）。
- 每個 event 包含 `run_id`、`event`、`level`、`timestamp`、`message`。
- 不記錄 raw XML、Authorization、cookie、token 或可能含 credential 的完整 query。
- exception stack trace 僅在 debug/diagnostics；使用者 summary 顯示 sanitized action message。

### Tests

- 新 domain 規則至少有 unit test。
- bug fix 必須先有可重現 regression test。
- network test 使用 fixture/fake server；一般 unit test 不依賴公開網路。
- 時間測試注入固定 clock，禁止依賴測試機當前日期。
- deterministic tests 至少比較兩次輸出 bytes 與 shuffled input。
- snapshot/golden files 必須小、可審查，不可用更新 snapshot 掩蓋行為改變。
- coverage 是診斷，不是目標；trust boundary、error path、identity 與 export invariant 不可省略。

## 4. Feed Registry Changes

新增 Feed：

1. 確認 URL 為公開 HTTP/HTTPS RSS/Atom endpoint。
2. 使用穩定小寫 kebab-case ID。
3. 確認 ID 與 URL 唯一，tags 排序。
4. 執行 offline validation 與一次 dry-run。
5. 在 PR 說明來源、預期語言、授權/公開性與 dry-run 結果。

不得將 token、credential、cookie 或私人 Feed URL commit 到 registry。

## 5. Schema Changes

- Optional additive field：提升 minor version，新增 examples、validation 與 compatibility test。
- Required/type/identity/semantics change：提升 major，新增 ADR 與 migration plan。
- Patch 只用於不改變資料契約語意的澄清/修正。
- 歷史資料預設不 rewrite；若必須 migration，PR 必須說明範圍、rollback 與 checksum/validation。
- 不得只修改 generated schema 而不修改 `docs/JSON_SCHEMA.md`。

## 6. Git and Branch Strategy

- Default branch 應受 branch protection。
- 每項工作由短生命週期 branch 完成，例如：
  - `feat/feed-health-export`
  - `fix/atom-timezone`
  - `docs/schema-compatibility`
- 禁止直接 push 或在本機 merge 到 default branch；所有合併必須經 GitHub Pull Request。
- 保持 PR focused；不混入格式化全 repository 或無關 refactor。
- daily collector bot 的 data commit 是 workflow 產物，不取代 source code PR review。

### Conventional Commits

格式：

```text
<type>(<optional scope>): <imperative summary>
```

允許 type：`feat`、`fix`、`docs`、`test`、`refactor`、`chore`、`ci`、`data`。

範例：

```text
feat(normalize): add deterministic URL identity
fix(atom): preserve updated timestamp timezone
docs(schema): define v1 compatibility policy
data: collect 2026-07-25
```

Breaking change 使用 footer `BREAKING CHANGE:`，且必須對應 major Schema/ADR。

## 7. Pull Request Requirements

PR 描述至少包含：

- 問題與動機。
- Scope / explicit non-scope。
- 對應 FR、AC、ADR 或 issue。
- 測試證據與 deterministic output 證據（適用時）。
- Schema/資料 migration 影響。
- Security、logging 與 rollback 影響。

### Pull Request Checklist

- [ ] 我先更新了受影響的 `docs/`。
- [ ] 我沒有加入超出需求的功能或 speculative abstraction。
- [ ] Ruff、Black、pytest 與 validate 全數通過。
- [ ] 新規則有 tests，bug fix 有 regression test。
- [ ] output 在固定 fixtures 下 deterministic。
- [ ] JSON、Markdown、Metadata、FeedHealth 與 indexes 保持一致。
- [ ] 新增 log 不包含 secrets/raw untrusted payload。
- [ ] Schema change 有正確版本與 compatibility 說明。
- [ ] Dependency change 有必要性、固定版本與 license/security 評估。
- [ ] 我沒有在本機 merge 到 default branch，也不要求 force push。

## 8. Review Guidelines

Reviewer 依序檢查：

1. 是否符合產品 scope（Collect/Normalize/Export）。
2. 文件與 implementation 是否一致。
3. trust boundary、日期、identity、dedup 與 atomicity 是否正確。
4. failure 是否 observable 且不造成 partial publish。
5. 是否能用更少的標準功能完成而不犧牲 correctness。
6. tests 是否證明 acceptance，而不是只覆蓋程式行數。

## 9. Security Reporting

不要在公開 issue 張貼 token、私人 Feed URL 或可利用的敏感細節。使用 repository 的 private security advisory（啟用後）聯絡 maintainer。修復不得把真實 secret 加入 fixture。

## 10. Definition of Ready / Done

### Ready

- 問題、scope、acceptance 明確。
- 所需 Schema/ADR 已識別。
- 不依賴未決的產品選擇。

### Done

- 文件、程式、tests、fixtures 同步。
- CI 全綠；review comments 已處理。
- 無不必要 dependency/abstraction。
- PR 在 GitHub 審查並合併；需要時 release/migration note 已發布。

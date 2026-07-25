# JSON Data Contracts

> 文件版本：1.0.0  
> Current Schema Version：`1.0.0`  
> 本文件是 JSON 欄位、型別與相容性規則的唯一事實來源。實作可由本規格產生正式 JSON Schema files，但不得另行改變語意。

## 1. Common Conventions

- 所有 JSON object 必須包含 `schema_version: "1.0.0"`。
- 時間使用 RFC 3339 UTC，格式 `YYYY-MM-DDTHH:mm:ssZ`；不輸出 local offset。
- 日期使用 ISO 8601 `YYYY-MM-DD`，其語意為 Asia/Taipei calendar date。
- URL 僅允許 absolute HTTP/HTTPS。
- ID 不得因執行時間、抓取順序或 `run_id` 改變。
- 未知欄位：同 major version 的 reader 應忽略；writer 不得輸出未規範欄位。
- `null` 只用於明確定義 nullable 的 optional scalar；集合缺值用 `[]`。
- 所有字串先 Unicode normalize（NFC），不得包含 NUL/control characters（tab/newline 規範欄位除外）。
- 陣列順序若未另述，必須 deterministic。
- 整數皆為非負十進位整數。

### Shared validations

| Name | Validation |
|---|---|
| `schema_version` | Semantic Version，current 為 `1.0.0` |
| `feed_id` | `^[a-z0-9][a-z0-9-]{1,62}$` |
| `article_id` | `^sha256:[0-9a-f]{64}$` |
| `run_id` | RFC 4122 UUID string |
| timestamp | `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` |
| date | `^\d{4}-\d{2}-\d{2}$` 且為有效日期 |
| repository path | relative POSIX path；不得以 `/` 開頭或包含 `..` |

## 2. Article Schema

### Purpose

代表經 normalization 與 deduplication 後的單篇文章。Article 通常嵌入 `DailyDigest.articles`，不單獨存檔。

### Required

| Field | Type | Validation / Semantics |
|---|---|---|
| `schema_version` | string | `1.0.0` |
| `id` | string | article_id；deterministic |
| `title` | string | 1–500 chars，trimmed、collapsed whitespace |
| `url` | string | normalized absolute HTTP/HTTPS URL，max 4096 |
| `source_feed_ids` | string[] | 1–100 unique values，升冪 |
| `published_at` | string | RFC 3339 UTC；是日期選擇的 effective published time |
| `authors` | string[] | unique、升冪，每項 1–200 chars |
| `categories` | string[] | unique、升冪，每項 1–100 chars |

### Optional

| Field | Type | Validation / Semantics |
|---|---|---|
| `guid` | string \| null | 原 Feed identifier，max 2048 |
| `summary` | string \| null | safe plain text，max 10,000 chars |
| `published_raw` | string \| null | 來源原始值，max 500 |
| `updated_at` | string \| null | RFC 3339 UTC |
| `updated_raw` | string \| null | 來源原始值，max 500 |
| `language` | string \| null | BCP 47-like tag，max 35；不猜測 |

### Identity validation

ID input 順序：

1. 有 canonical URL：`"url\n" + url`
2. 否則有 GUID：`"guid\n" + primary_feed_id + "\n" + guid`
3. 否則：`"fallback\n" + primary_feed_id + "\n" + title + "\n" + published_at`

對 UTF-8 bytes 計算 SHA-256，再加 `sha256:`。因正式 Article 要求 URL，無 URL 的候選 entry 在 v1 會被拒絕；第 2/3 路徑保留給 parser 先產生 identity 與 health 診斷，不代表可 export。

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "id": "sha256:7d96c8f2fe2fd81b90b96c479290e048cc5e38f213c5058f91bf89940874ec20",
  "title": "Example Feed 發布新文章",
  "url": "https://example.com/articles/42?lang=zh",
  "source_feed_ids": [
    "example-tech"
  ],
  "published_at": "2026-07-25T00:15:00Z",
  "authors": [
    "王小明"
  ],
  "categories": [
    "technology"
  ],
  "guid": "article-42",
  "summary": "這是 Feed 提供的純文字摘要。",
  "published_raw": "Fri, 25 Jul 2026 08:15:00 +0800",
  "updated_at": null,
  "updated_raw": null,
  "language": "zh-TW"
}
```

## 3. Feed Schema

### Purpose

描述 `config/feeds.json` 中的一個來源。Feed registry 自身是一個 object，包含 `schema_version` 與 `feeds` array。

### Required

| Field | Type | Validation / Semantics |
|---|---|---|
| `schema_version` | string | Feed object current version |
| `id` | string | feed_id；registry 內唯一 |
| `title` | string | 1–200 chars |
| `url` | string | absolute HTTP/HTTPS，registry 內 URL 唯一 |
| `enabled` | boolean | 是否參與 collection |
| `tags` | string[] | unique、升冪，每項符合 `^[a-z0-9][a-z0-9-]{0,49}$` |

### Optional

| Field | Type | Validation / Semantics |
|---|---|---|
| `homepage_url` | string \| null | absolute HTTP/HTTPS |
| `language` | string \| null | BCP 47-like tag |
| `notes` | string \| null | 維運說明，max 1000，不輸出至 Article |

### Registry validation

- top-level required：`schema_version`、`feeds`。
- `feeds` 可為空，但 production workflow 應視「無 enabled Feed」為 configuration error。
- Feed 依 `id` 升冪保存，減少 diff。
- 不允許 per-feed executable hook、credential 或 parser code。

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "feeds": [
    {
      "schema_version": "1.0.0",
      "id": "example-tech",
      "title": "Example Tech",
      "url": "https://example.com/feed.xml",
      "enabled": true,
      "tags": [
        "technology"
      ],
      "homepage_url": "https://example.com/",
      "language": "zh-TW",
      "notes": null
    }
  ]
}
```

## 4. Metadata Schema

### Purpose

描述某次已發布 daily collection 的 run facts 與整體狀態，保存於每日 `metadata.json`。此檔包含非 deterministic 的 runtime facts；不參與 Article identity。

### Required

| Field | Type | Validation / Semantics |
|---|---|---|
| `schema_version` | string | `1.0.0` |
| `run_id` | string | UUID |
| `collection_date` | string | Asia/Taipei date |
| `timezone` | string | 固定 `Asia/Taipei` |
| `started_at` | string | UTC timestamp |
| `completed_at` | string | UTC timestamp，≥ started_at |
| `duration_ms` | integer | ≥ 0 |
| `status` | string | `success` 或 `partial`；failed run 不發布 Metadata |
| `trigger` | string | `schedule`、`workflow_dispatch`、`local` |
| `feed_counts` | object | 見下方 |
| `entry_counts` | object | 見下方 |
| `artifacts` | object | 四個 daily artifact 的 relative paths |

`feed_counts` required keys：`configured`、`enabled`、`disabled`、`succeeded`、`failed`。  
`entry_counts` required keys：`seen`、`selected`、`exported`、`duplicate`、`skipped_invalid_date`、`skipped_invalid_entry`。

### Optional

| Field | Type | Validation / Semantics |
|---|---|---|
| `github_run_id` | string \| null | GitHub-provided opaque ID |
| `commit_sha_before` | string \| null | 40/64 hex SHA；執行前 revision |
| `collector_version` | string \| null | application SemVer |

### Cross-field validation

- `configured = enabled + disabled`。
- `enabled = succeeded + failed`。
- `status=success` iff `failed=0`；otherwise `partial` 且 `succeeded>=1`。
- `exported = DailyDigest.article_count`。
- artifact paths 的 prefix 必須等於 collection date path。

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "run_id": "d62f2054-aed2-48f3-b24c-0a02cf3047ac",
  "collection_date": "2026-07-25",
  "timezone": "Asia/Taipei",
  "started_at": "2026-07-24T23:30:04Z",
  "completed_at": "2026-07-24T23:30:18Z",
  "duration_ms": 14000,
  "status": "partial",
  "trigger": "schedule",
  "feed_counts": {
    "configured": 4,
    "enabled": 3,
    "disabled": 1,
    "succeeded": 2,
    "failed": 1
  },
  "entry_counts": {
    "seen": 84,
    "selected": 12,
    "exported": 10,
    "duplicate": 2,
    "skipped_invalid_date": 3,
    "skipped_invalid_entry": 1
  },
  "artifacts": {
    "markdown": "data/2026/07/25/README.md",
    "digest": "data/2026/07/25/articles.json",
    "metadata": "data/2026/07/25/metadata.json",
    "feed_health": "data/2026/07/25/feed_health.json"
  },
  "github_run_id": "22123456789",
  "commit_sha_before": "0123456789abcdef0123456789abcdef01234567",
  "collector_version": "1.0.0"
}
```

## 5. DailyDigest Schema

### Purpose

每日文章集合的 canonical machine-readable representation，保存為 `articles.json`。

### Required

| Field | Type | Validation / Semantics |
|---|---|---|
| `schema_version` | string | `1.0.0` |
| `collection_date` | string | Asia/Taipei date |
| `timezone` | string | `Asia/Taipei` |
| `article_count` | integer | 等於 `articles.length` |
| `articles` | Article[] | unique ID；published_at desc、id asc |

### Optional

無。v1 刻意保持 canonical digest 精簡；執行資訊屬於 Metadata。

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "collection_date": "2026-07-25",
  "timezone": "Asia/Taipei",
  "article_count": 1,
  "articles": [
    {
      "schema_version": "1.0.0",
      "id": "sha256:7d96c8f2fe2fd81b90b96c479290e048cc5e38f213c5058f91bf89940874ec20",
      "title": "Example Feed 發布新文章",
      "url": "https://example.com/articles/42?lang=zh",
      "source_feed_ids": [
        "example-tech"
      ],
      "published_at": "2026-07-25T00:15:00Z",
      "authors": [
        "王小明"
      ],
      "categories": [
        "technology"
      ],
      "guid": "article-42",
      "summary": "這是 Feed 提供的純文字摘要。",
      "published_raw": "Fri, 25 Jul 2026 08:15:00 +0800",
      "updated_at": null,
      "updated_raw": null,
      "language": "zh-TW"
    }
  ]
}
```

## 6. FeedHealth Schema

### Purpose

描述單次執行中每個 enabled Feed 的可觀測結果，保存為每日 `feed_health.json`。

### Required

Top-level：

| Field | Type | Validation |
|---|---|---|
| `schema_version` | string | `1.0.0` |
| `run_id` | string | 與 Metadata 相同 |
| `collection_date` | string | 與 DailyDigest 相同 |
| `feeds` | FeedHealthItem[] | 每個 enabled Feed 恰一筆，feed_id 升冪 |

FeedHealthItem：

| Field | Type | Validation / Semantics |
|---|---|---|
| `feed_id` | string | feed_id |
| `status` | string | `succeeded` 或 `failed` |
| `started_at` | string | UTC |
| `completed_at` | string | UTC |
| `duration_ms` | integer | ≥ 0 |
| `attempts` | integer | 1–3 |
| `entries_seen` | integer | ≥ 0 |
| `entries_selected` | integer | ≥ 0 |
| `entries_exported` | integer | ≥ 0；跨 Feed dedup 時僅為 provenance count，不可加總推導 digest count |
| `entries_skipped` | integer | ≥ 0 |
| `warnings` | string[] | stable warning codes，unique、升冪 |

### Optional

| Field | Type | Validation / Semantics |
|---|---|---|
| `http_status` | integer \| null | 100–599 |
| `final_url` | string \| null | HTTP/HTTPS，敏感 query 已 redact |
| `content_type` | string \| null | max 200 |
| `etag` | string \| null | max 1000 |
| `last_modified` | string \| null | HTTP header raw value，max 500 |
| `error` | object \| null | failed 時 required；見下方 |

Error object required：`code`、`stage`、`message`、`retryable`。  
`stage` enum：`fetch`、`parse`、`normalize`。`message` 必須 sanitised，max 2000。

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "run_id": "d62f2054-aed2-48f3-b24c-0a02cf3047ac",
  "collection_date": "2026-07-25",
  "feeds": [
    {
      "feed_id": "example-tech",
      "status": "succeeded",
      "started_at": "2026-07-24T23:30:05Z",
      "completed_at": "2026-07-24T23:30:06Z",
      "duration_ms": 1000,
      "attempts": 1,
      "entries_seen": 20,
      "entries_selected": 3,
      "entries_exported": 3,
      "entries_skipped": 0,
      "warnings": [],
      "http_status": 200,
      "final_url": "https://example.com/feed.xml",
      "content_type": "application/atom+xml",
      "etag": "\"abc123\"",
      "last_modified": "Fri, 25 Jul 2026 00:20:00 GMT",
      "error": null
    },
    {
      "feed_id": "unavailable-feed",
      "status": "failed",
      "started_at": "2026-07-24T23:30:05Z",
      "completed_at": "2026-07-24T23:30:15Z",
      "duration_ms": 10000,
      "attempts": 3,
      "entries_seen": 0,
      "entries_selected": 0,
      "entries_exported": 0,
      "entries_skipped": 0,
      "warnings": [],
      "http_status": 503,
      "final_url": "https://feeds.example.net/rss",
      "content_type": null,
      "etag": null,
      "last_modified": null,
      "error": {
        "code": "FETCH_HTTP_503",
        "stage": "fetch",
        "message": "Feed server returned HTTP 503 after 3 attempts.",
        "retryable": true
      }
    }
  ]
}
```

## 7. Latest Schema

### Purpose

固定位置 `data/latest.json` 的 pointer，讓 consumer 不掃描 archive 即可找到最近有效日期。

### Required

| Field | Type | Validation / Semantics |
|---|---|---|
| `schema_version` | string | `1.0.0` |
| `collection_date` | string | Index 中最大有效日期 |
| `status` | string | 該日 `success` 或 `partial` |
| `article_count` | integer | 與該日 DailyDigest 相同 |
| `digest_path` | string | repository-relative path |
| `markdown_path` | string | repository-relative path |
| `metadata_path` | string | repository-relative path |
| `feed_health_path` | string | repository-relative path |

### Optional

無。若 archive 尚無任何有效日期，`latest.json` 不存在，不輸出 null pointer。

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "collection_date": "2026-07-25",
  "status": "partial",
  "article_count": 10,
  "digest_path": "data/2026/07/25/articles.json",
  "markdown_path": "data/2026/07/25/README.md",
  "metadata_path": "data/2026/07/25/metadata.json",
  "feed_health_path": "data/2026/07/25/feed_health.json"
}
```

## 8. Archive Schema

### Purpose

固定位置 `data/archive.json` 的階層式 discovery index，按年/月聚合。

### Required

| Field | Type | Validation / Semantics |
|---|---|---|
| `schema_version` | string | `1.0.0` |
| `total_days` | integer | 所有 month day_count 加總 |
| `total_articles` | integer | 所有 month article_count 加總 |
| `years` | ArchiveYear[] | year 降冪 |

ArchiveYear required：`year`（`^\d{4}$`）、`day_count`、`article_count`、`months`。  
ArchiveMonth required：`month`（`^(0[1-9]|1[0-2])$`）、`day_count`、`article_count`、`days`。  
ArchiveDay required：`collection_date`、`status`、`article_count`、`digest_path`、`markdown_path`。  
`months` 按 month 降冪；`days` 按 collection_date 降冪。

### Optional

無。彙總值皆可由 days 推導，但作為 consumer 快速導航的 materialized index。

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "total_days": 1,
  "total_articles": 10,
  "years": [
    {
      "year": "2026",
      "day_count": 1,
      "article_count": 10,
      "months": [
        {
          "month": "07",
          "day_count": 1,
          "article_count": 10,
          "days": [
            {
              "collection_date": "2026-07-25",
              "status": "partial",
              "article_count": 10,
              "digest_path": "data/2026/07/25/articles.json",
              "markdown_path": "data/2026/07/25/README.md"
            }
          ]
        }
      ]
    }
  ]
}
```

## 9. Index Schema

`data/index.json` 是 `Archive` 的扁平 counterpart，產品需求中的 Index 使用此契約。

### Required

| Field | Type | Validation |
|---|---|---|
| `schema_version` | string | `1.0.0` |
| `day_count` | integer | 等於 `days.length` |
| `days` | IndexDay[] | collection_date 降冪、日期唯一 |

IndexDay required：`collection_date`、`status`、`article_count`、`digest_path`、`metadata_path`。

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "day_count": 1,
  "days": [
    {
      "collection_date": "2026-07-25",
      "status": "partial",
      "article_count": 10,
      "digest_path": "data/2026/07/25/articles.json",
      "metadata_path": "data/2026/07/25/metadata.json"
    }
  ]
}
```

## 10. Schema Versioning and Backward Compatibility

採 Semantic Versioning：

- **Patch**：文字澄清或 validation bug fix，不改變合法資料集合的預期語意。
- **Minor**：只新增 optional field、enum 可安全忽略的值，或新 artifact；既有 reader 應可繼續讀取。
- **Major**：刪除/重新命名欄位、改 required、改型別、改 identity/日期/排序語意。

Writer rules：

1. 每個文件寫入實際契約版本，不以 application version 代替。
2. 同一 daily export 的所有 v1 artifacts 應使用相同 major version。
3. major upgrade 必須新增 ADR、migration plan、fixtures 與至少一版 dual-read 或明確 repository migration。
4. 歷史 archive 預設不批次重寫；reader 必須按 major version dispatch。

Reader rules：

1. 支援同 major 的 reader 必須忽略未知欄位。
2. 遇到未知 major 必須 fail clearly，不可 best-effort 猜測。
3. 不得以欄位缺失猜測版本。
4. nullable 與 missing 的語意不可互換，除非該 minor version 明確規定。

Compatibility matrix：

| Writer | Reader 1.0 | Expected |
|---|---|---|
| 1.0.x | 1.0.x | Fully compatible |
| 1.x（新增 optional） | 1.0.x | Reader 忽略未知欄位 |
| 2.x | 1.x | Incompatible；reader 必須拒絕 |

## 11. Cross-document Validation

發布前必須一次驗證：

- DailyDigest、Metadata、FeedHealth 的 collection date 一致。
- Metadata、FeedHealth 的 run_id 一致。
- Metadata exported count 等於 DailyDigest article_count。
- success/partial 與 FeedHealth 統計一致。
- Markdown article ID/order 是 DailyDigest 的精確 projection。
- Latest、Index、Archive 指向的檔案存在且 count/status 相同。
- 所有 path 均位於 `data/` 且無 path traversal。
- 所有 Article published_at 換算為 Asia/Taipei 後落於 collection date。

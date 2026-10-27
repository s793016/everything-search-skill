---
name: everything-search
description: "Instant file/folder search on this Windows machine via the Everything SDK (Everything64.dll through ctypes). Use for ANY request to find, locate, or list files or folders by name, extension, size, date, path, or duplicates (e.g. 找檔案, 哪裡有, 昨天下載的, 最大的影片, where is X, find all *.log) — prefer it over Glob, find, Get-ChildItem -Recurse or dir /s when the search is outside the current project or spans whole drives. Not for searching file contents."
---

# Everything Search

Search files and folders on Windows instantly by calling the Everything SDK DLL directly via ctypes — no MCP server, no recursive disk scan. **165s recursive scan → ~1s.**

It searches names/paths only (Everything's index), not file contents. For text inside files in a project, use Grep.

## ⚠️ Token Budget Rules

**Never dump hundreds of results into context.** Always paginate:

- `-n` / `--max-results`: **default 10, never exceed 20** unless the user asks
- `-o` / `--offset`: page 1 = 0, page 2 = 10, …
- The output shows `Found X of TOTAL` — tell the user the total, and fetch more pages only when asked

## Usage

Run with the Bash tool (works the same from PowerShell). If the skill is installed elsewhere (e.g. a project's `.claude/skills/`), adjust the path:

```bash
python "~/.claude/skills/everything-search/scripts/everything_search.py" "QUERY" [-n 10] [-o 0] [-s SORT] [--json]
```

Examples:

```bash
# Basic
python "~/.claude/skills/everything-search/scripts/everything_search.py" "config.yaml" -n 10

# Page 2 (results 11-20)
python "~/.claude/skills/everything-search/scripts/everything_search.py" "config.yaml" -n 10 -o 10

# Python files modified today, newest first
python "~/.claude/skills/everything-search/scripts/everything_search.py" "ext:py dm:today" -n 5 -s modified-desc

# Biggest videos on C:
python "~/.claude/skills/everything-search/scripts/everything_search.py" "path:C:\ size:>500mb ext:mp4|mkv|avi|mov" -n 10 -s size-desc

# JSON (path, filename, extension, size, created, modified, accessed, attributes, run_count)
python "~/.claude/skills/everything-search/scripts/everything_search.py" "test" -n 10 --json
```

Other flags: `--match-path`, `--case`, `--whole-word`, `--regex` (same as the `path:`, `case:`, `ww:`, `regex:` modifiers in the query).

Quoting: wrap the whole query in double quotes for Bash. If the query itself contains `"` (e.g. `path:"My Documents"`), wrap it in single quotes instead: `'path:"My Documents"\ invoice'`. Chinese and other non-ASCII queries work; output is forced to UTF-8.

## Search Syntax (Everything SDK — full power)

### Basic Operators
- Space = AND, `|` = OR, `!` = NOT
- `"exact phrase"` for phrases
- `*` wildcard, `?` single char

### Functions
- **Size:** `size:>100mb`, `size:<1kb`, `size:1..10mb`
- **Date:** `datemodified:today`, `dm:2024-01-01`, `datecreated:yesterday`
- **Type:** `ext:py`, `ext:py|js|ts`, `type:Folder`
- **Path:** `path:C:\Projects`, `nosubfolders:C:\Temp`
- **Name:** `startwith:config`, `endwith:.log`
- **Duplicates:** `sizedupe`, `dmdupe`, `namepartdupe`
- **Folders:** `child:readme.txt`, `empty`

### Modifiers
- `case:`, `nocase:` — case sensitivity
- `file:`, `folder:` — file or folder only
- `path:`, `nopath:` — match full path or filename
- `regex:`, `noregex:` — regex mode
- `wholeword:`, `ww:` — whole words only

### Sort Options (`-s` / `--sort`)
- `name` / `name-desc` (1 / 2)
- `path` / `path-desc` (3 / 4)
- `size` / `size-desc` (5 / 6)
- `created` / `created-desc` (11 / 12)
- `modified` / `modified-desc` (13 / 14)
- Any other raw SDK sort number also works (e.g. `22` = recently changed, newest first)

## Natural Language → SDK Query Mapping

When user describes something in natural language, convert to Everything SDK syntax.

### Time-based queries
| User says | SDK query |
|-----------|-----------|
| "昨天下載的壓縮包" | `ext:zip|rar|7z datemodified:yesterday` |
| "上周導出的發票 Excel" | `ext:xlsx|xls datemodified:lastweek invoice` |
| "最近三天修改過的代碼" | `ext:py|js|ts|java|go datemodified:3daysago` |
| "今年生成的 PDF 合同" | `ext:pdf datemodified:thisyear contract` |
| "上个月改过的 PPT" | `ext:pptx|ppt datemodified:lastmonth` |
| "昨晚8點之後的日誌" | `ext:log datemodified:yesterday` |
| "去年所有對帳單" | `ext:xlsx|pdf datemodified:lastyear` |

### File type / extension queries
| User says | SDK query |
|-----------|-----------|
| "所有 design 關鍵字 PSD" | `ext:psd design` |
| "所有 .env 文件" | `.env` |
| "所有 mkv 影片" | `ext:mkv` |
| "所有 README Markdown" | `readme ext:md` |
| "所有 config 結尾 YAML" | `endwith:config ext:yml|yaml` |
| "所有 key/pem 證書" | `ext:key|pem|crt|cer` |

### Location / path queries
| User says | SDK query |
|-----------|-----------|
| "Downloads 大包安裝檔" | `path:Downloads\ size:>100mb ext:exe|msi|dmg` |
| "桌面 PDF" | `path:Desktop\ ext:pdf` |
| "project-x 目錄日誌" | `path:project-x\ ext:log` |
| "D盤 workspace 圖片" | `path:D:\workspace\ ext:jpg|png|gif|svg` |
| "我的文檔 發票相關" | `path:"My Documents"\ invoice` |
| "VSCode 設定 JSON" | `path:Code\User\ ext:json` |

### Keyword combinations (AND/OR/NOT)
| User says | SDK query |
|-----------|-----------|
| "design 和 review 的文件" | `design review` |
| "invoice 或 bill 的 Excel" | `invoice\|bill ext:xlsx|xls` |
| "draft 但不含 backup" | `draft !backup` |
| "名字有 v2 和 final" | `v2 final` |
| "2024 或 2025 年規劃" | `2024\|2025 plan` |

### Cleanup / troubleshooting
| User says | SDK query |
|-----------|-----------|
| "C 盤大影片準備刪" | `path:C:\ size:>500mb ext:mp4|mkv|avi|mov` |
| "最近7天 1GB+ 日誌" | `ext:log datemodified:thisweek size:>1gb` |
| "重複圖片清空間" | `sizedupe ext:jpg|png|gif` |
| "所有空資料夾" | `empty` |
| "小於 10KB 可疑設定" | `size:<10kb ext:cfg|ini|yaml|json|xml` |
| "下載目錄超過 5GB 壓縮檔" | `path:Downloads\ size:>5gb ext:zip|rar|7z|iso` |

### Dev / Ops
| User says | SDK query |
|-----------|-----------|
| "最近改的 docker-compose" | `docker-compose ext:yml|yaml datemodified:today` |
| "上周改的 K8s YAML" | `ext:yaml datemodified:lastweek kubernetes\|k8s\|deploy` |
| "含 test 的 Python 測試" | `ext:py test` |
| "最近一天的 .log" | `ext:log datemodified:today` |
| "含 error 和 production 的日誌" | `error production ext:log` |
| "所有 .map source map" | `ext:map` |
| "所有 package-lock / pnpm-lock" | `lock ext:json` |

### Content search (via regex on filenames)
| User says | SDK query |
|-----------|-----------|
| "美剧第幾集 rmvb" | `regex:".*\.S\d{2}E\d{2}\..*\.rmvb"` |
| "日期命名日誌 20240623.log" | `regex:"\d{8}\.log"` |
| "版本號安裝包 v1.2.3" | `regex:"v\d+\.\d+\.\d+"` |
| "連續分卷壓縮 part1/2/3" | `regex:"part\d+"` |
| "6位數字ID的圖片" | `regex:"\d{6}\.(jpg|png)"` |

### Office / daily
| User says | SDK query |
|-----------|-----------|
| "2024 年度工作總結" | `2024 總結 ext:docx|doc|pdf` |
| "會議紀要 Word" | `meeting\|minutes ext:docx|doc` |
| "帶'簡歷'的 PDF" | `resume\|簡歷\|CV ext:pdf` |
| "帶'投遞'的簡歷" | `投遞 ext:pdf|docx` |
| "keynote 演示稿" | `keynote ext:key|keynote` |

### Multi-dimensional combinations
| User says | SDK query |
|-----------|-----------|
| "上周 Downloads 驅動安裝包" | `path:Downloads\ driver ext:inf|exe|msi datemodified:lastweek` |
| "今年 project-x 效能測試報告" | `path:project-x\ performance\|benchmark ext:pdf|xlsx datemodified:thisyear` |
| "桌面最近修改 Excel" | `path:Desktop\ ext:xlsx|xls datemodified:today` |
| "workspace 1GB+ 日誌" | `path:workspace\ size:>1gb ext:log` |
| "我的文檔近三個月發票 PDF" | `path:"My Documents"\ invoice ext:pdf datemodified:90daysago` |

## ⚠️ Slow Queries (date created / unindexed properties)

By default Everything indexes **date modified** but not **date created**. A bare `dc:` / `datecreated:` query (or `-s created-desc` on a big result set) makes Everything read every file's metadata from disk (network shares included) and can hang for minutes.

- Always pre-filter `dc:` with an indexed term: `dm:>=2026-10-27 dc:2026-10-27` (a file created on day X was modified on or after X) → ~2s
- Prefer `-s modified-desc` over `created-desc` unless the result set is already small
- Add a timeout when unsure: `timeout 30 python ...`
- "New files on day X" returns tens of thousands of cache/log files; exclude noise:
  `'file: dm:>=X dc:X !AppData\ !gecko-profile\ !C:\Windows\ !C:\ProgramData\ !$RECYCLE.BIN\ !\.git\ !node_modules\ !__pycache__\ !C:\Program'`

## Troubleshooting

- **"Cannot load Everything SDK DLL"** — The DLL is looked up in this order: `$EVERYTHING_SDK_PATH` → `scripts/Everything64.dll` (next to the script). Get the DLL from the Everything SDK: https://www.voidtools.com/support/everything/sdk/
- **"IPC failed"** — Everything is not running. Check `sc query Everything` (should be RUNNING) or start Everything.exe
- **Empty results** — The drive may not be indexed. Everything → Tools → Options → Folders/NTFS → add the drive
- **Odd regex results** — The script converts `/` to `\` in the query, so avoid forward slashes in `regex:` patterns

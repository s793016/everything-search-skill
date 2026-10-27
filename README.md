# everything-search — Claude Code skill

Instant file/folder search on Windows for [Claude Code](https://claude.com/claude-code), powered by [voidtools Everything](https://www.voidtools.com/).

The skill calls the Everything SDK (`Everything64.dll`) directly through Python `ctypes` — no MCP server, no recursive disk scan. A search that takes minutes with `find` / `Get-ChildItem -Recurse` returns in about a second.

- Full Everything query syntax (`ext:`, `size:`, `dm:`, `path:`, `regex:`, `sizedupe`, …)
- Pagination and sorting, kept small by default so results don't flood the context
- Natural-language → query mapping table (Chinese and English examples) so Claude can turn "昨天下載的壓縮包" into `ext:zip|rar|7z dm:yesterday`
- Text or JSON output, UTF-8 safe for non-ASCII paths

## Requirements

- Windows, 64-bit
- [Everything](https://www.voidtools.com/downloads/) installed and running (service mode recommended)
- Python 3.9+
- `Everything64.dll` from the [Everything SDK](https://www.voidtools.com/support/everything/sdk/) (not included in this repo; the normal Everything installer does not ship it)

## Install

```bash
git clone https://github.com/s793016/everything-search-skill.git ~/.claude/skills/everything-search
```

Then download the Everything SDK, extract `dll/Everything64.dll` and either:

- copy it to `~/.claude/skills/everything-search/scripts/Everything64.dll`, or
- set the `EVERYTHING_SDK_PATH` environment variable to its full path.

Start a new Claude Code session; the skill is picked up automatically and used whenever you ask to find files.

## Command-line use

The script also works on its own:

```bash
python ~/.claude/skills/everything-search/scripts/everything_search.py "ext:py dm:today" -n 5 -s modified-desc
```

| Flag | Meaning |
|------|---------|
| `-n`, `--max-results` | Results per page (default 10) |
| `-o`, `--offset` | Pagination offset |
| `-s`, `--sort` | `name`, `path`, `size`, `created`, `modified` (append `-desc`), or a raw SDK sort number |
| `--match-path`, `--case`, `--whole-word`, `--regex` | Search modifiers |
| `--json` | JSON output |

## Tip: searching by creation date

Everything indexes date modified but not date created by default, so a bare `dc:2026-10-27` makes it read every file from disk and can hang for minutes. Pre-filter with an indexed term instead:

```
dm:>=2026-10-27 dc:2026-10-27
```

See [SKILL.md](SKILL.md) for the full query reference.

## License

MIT for the code in this repo. Everything and the Everything SDK are © voidtools and covered by their own license.

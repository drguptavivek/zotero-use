# Setup Troubleshooting

Load this for failures after using `references/pyzotero-cli.md` or `references/zotero-mcp.md`.

## Self-Test

Run the dependency-free self-test before individual troubleshooting steps:

```bash
python3 scripts/selftest.py
```

Use strict mode when the current task requires both the `zot` command and a working Zotero desktop local API connection:

```bash
python3 scripts/selftest.py --strict
```

The command installs nothing and does not print Zotero library contents, API keys, or profile contents. It also discovers the live tools at `http://localhost:23119/zotseek/mcp`; an unavailable optional ZOTseek endpoint is a warning. Use `--require-zotseek` when semantic search is required, `--json` for machine-readable results, and `--skip-local` when Zotero desktop access is intentionally unavailable.

## Pyzotero CLI Checks

```bash
command -v zot
zot --help
uv tool list | rg -i 'pyzotero|zotero'
```

If `zot` is missing:

```bash
uv tool install pyzotero-cli -U
uv tool update-shell
hash -r
```

If the user does not want a persistent installation, verify and run it ephemerally instead:

```bash
uvx --from pyzotero-cli zot --help
```

If local mode fails:

- Confirm Zotero is open.
- Confirm Zotero Settings -> Advanced -> Allow other applications on this computer to communicate with Zotero is enabled.
- Use `--local --library-id 0 --library-type user` before the command group.

## API/Profile Checks

For API-backed profiles:

- Personal library type is `user`.
- Group library type is `group`.
- Config file: `~/.config/zotcli/config.ini`.
- Precedence: command-line flags, environment variables, active profile.

Relevant environment variables:

```bash
ZOTERO_API_KEY
ZOTERO_LIBRARY_ID
ZOTERO_LIBRARY_TYPE
```

Do not expose API keys in responses or logs.

## MCP Checks

If using Zotero MCP externally:

```bash
command -v zotero-mcp
zotero-mcp version
zotero-mcp setup-info
zotero-mcp db-status
```

If search/database behavior looks stale:

```bash
zotero-mcp update-db --force-rebuild
```

## DOCX Validation Checks

Validate narrow Zotero citation edits with the bundled read-only, standard-library script:

```bash
python3 scripts/validate_zotero_docx.py file.docx --minimum-fields 1
```

Use `--json` for machine-readable diagnostics. If Python 3 is unavailable, use the structural checks provided by the host document skill. Do not install a dependency solely for validation.

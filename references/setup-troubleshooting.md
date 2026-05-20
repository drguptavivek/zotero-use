# Setup Troubleshooting

Load this for failures after using `references/pyzotero-cli.md` or `references/zotero-mcp.md`.

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

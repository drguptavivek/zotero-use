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

## DOCX Render Checks

Routine Zotero citation insertion should use structural OOXML validation, not full rendering.

If the user explicitly asks for full DOCX visual QA, use the dedicated render venv:

```bash
PATH=~/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin \
TMPDIR=/private/tmp \
~/.local/venvs/docx-render/bin/python \
~/.codex/plugins/cache/openai-primary-runtime/documents/26.515.10909/skills/documents/render_docx.py \
file.docx \
--output_dir /private/tmp/docx-render-output \
--emit_pdf --verbose
```

Do not use the default `python3` for this renderer on this Mac; `pdf2image` is installed in `~/.local/venvs/docx-render`, not in Homebrew's externally managed Python.

Do not replace `~/.local/bin/soffice` with a symlink. It must remain a wrapper that execs the real LibreOffice app-bundle binary, because launching LibreOffice through a symlink caused headless conversion hangs.

If `soffice` quits unexpectedly, exits `-6`/`-1`, or `render_docx.py` reports failure to produce PDF despite the fixed venv and wrapper, rerun the render command outside the sandbox/escalated. This has been verified to succeed on this Mac and produce `<stem>.pdf` plus `page-*.png`.

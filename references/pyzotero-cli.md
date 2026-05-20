# Pyzotero CLI

Use this when the task needs Zotero search, browse, metadata, collections, tags, item children, citations, or setup through the low-context terminal route.

## Install As Shell Command

```bash
uv tool install pyzotero-cli -U
uv tool update-shell
hash -r
command -v zot
zot --help
```

The installed command is `zot`.

## Local Read-Only Mode

Requires Zotero 7 local API enabled:

Zotero Settings -> Advanced -> Allow other applications on this computer to communicate with Zotero.

Use `--local` before the command group:

```bash
zot --local --library-id 0 --library-type user items list --limit 5 --output table
zot --local --library-id 0 --library-type user items list --query "glaucoma" --qmode everything --limit 5 --output table
zot --local --library-id 0 --library-type user items get QUDEVEEJ --output table
zot --local --library-id 0 --library-type user items children QUDEVEEJ --output table
zot --local --library-id 0 --library-type user collections list --top --output table
zot --local --library-id 0 --library-type user util item-types
```

Local mode is read-only. Use it for GET-style operations.

## Profiles

For persistent API-backed use:

```bash
zot configure setup
zot configure setup --profile work_group
zot configure list-profiles
zot configure current-profile work_group
zot --profile work_group items list --limit 5 --output table
```

Configuration lives in `~/.config/zotcli/config.ini`.

Precedence:

1. Command-line flags such as `--api-key`, `--library-id`, `--library-type`, `--profile`
2. Environment variables such as `ZOTERO_API_KEY`, `ZOTERO_LIBRARY_ID`, `ZOTERO_LIBRARY_TYPE`
3. Active profile

## Common Commands

```bash
zot --local --library-id 0 --library-type user items list --filter-item-type journalArticle --sort dateModified --direction desc --limit 10 --output table
zot --local --library-id 0 --library-type user collections list --top --output table
zot --local --library-id 0 --library-type user tags list --output table
zot --local --library-id 0 --library-type user items children ITEM_KEY --output table
zot --local --library-id 0 --library-type user files download ATTACHMENT_KEY -o ./paper.pdf
zot --local --library-id 0 --library-type user fulltext get ATTACHMENT_KEY
zot --local --library-id 0 --library-type user items bib ITEM_KEY --output bibtex
zot --local --library-id 0 --library-type user items citation ITEM_KEY --output csljson
```

Use table output for human-readable summaries and JSON for machine processing.

Do not paste large JSON or full text unless the user asks for it.

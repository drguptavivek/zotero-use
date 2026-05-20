# Zotero MCP

Use this only when the user explicitly prefers MCP, asks for MCP setup, or Zotero MCP tools are already active and useful.

## Policy

- Do not add MCP config to `.agents`, Codex skill metadata, or agent config by default.
- Warn that adding MCP tools to an agent session consumes context/tool-list budget.
- Prefer Pyzotero CLI for routine terminal search and browsing.
- If the user still prefers MCP, recommend running the MCP server externally.

Upstream project: https://github.com/54yyyu/zotero-mcp

## External Server Commands

For stdio MCP clients:

```bash
zotero-mcp serve --transport stdio
```

For HTTP/SSE clients:

```bash
zotero-mcp serve --transport sse --host localhost --port 8000
```

For tunneled web clients, use `/sse/` with a trailing slash and a UUIDv4 `session_id`:

```text
https://example.ngrok-free.app/sse/?session_id=<uuidv4>
```

## Available MCP Tools

Use these only when active in the session:

- `zotero_search_items`
- `zotero_get_item_metadata`
- `zotero_get_item_fulltext`
- `zotero_get_collections`
- `zotero_get_collection_items`
- `zotero_get_item_children`
- `zotero_get_tags`
- `zotero_get_recent`

Prefer metadata before full text. Full text can be large and should be limited to shortlisted items.

## Diagnostics

```bash
zotero-mcp setup-info
zotero-mcp db-status
zotero-mcp update-db --force-rebuild
```

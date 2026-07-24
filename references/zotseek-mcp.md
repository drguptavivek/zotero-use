# ZOTseek MCP Semantic Search

Use this optional local backend for conceptual discovery, related-paper exploration, and passage-level semantic search over the indexed Zotero library.

Default endpoint:

```text
http://localhost:23119/zotseek/mcp
```

## Discover Before Calling

On the first ZOTseek use in a task, enumerate the live tools and inspect their descriptions and input schemas:

```bash
python3 scripts/zotseek_mcp.py tools
```

Do not assume a fixed set of tool names or arguments. The bundled client initializes the MCP server and calls `tools/list` before every call, then rejects names that the live server did not advertise. If the agent already has this MCP server connected natively, use its MCP discovery mechanism instead and follow the same discover-first rule.

The endpoint can be overridden without editing the skill:

```bash
ZOTSEEK_MCP_URL=http://localhost:23119/zotseek/mcp python3 scripts/zotseek_mcp.py tools
```

## Call A Discovered Tool

After reading the live schema, call the relevant discovered tool generically:

```bash
python3 scripts/zotseek_mcp.py call search --arguments '{"query":"community glaucoma screening implementation","max_results":10}'
```

`search`, `find_similar`, and `index_status` were advertised by ZOTseek 1.18.0 when this integration was tested, but they are examples rather than a contract. Prefer an index-status tool first when the live discovery output offers one. Use hybrid or semantic search for conceptual questions and structured `zot` commands for exact item retrieval, metadata confirmation, attachments, and full text.

ZOTseek is a read-only discovery path in this skill. Preserve returned Zotero item keys and deep links, then verify shortlisted items through `zot` before citation decisions.

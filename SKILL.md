---
name: zotero-use
description: "Use when an agent needs either of the two primary Zotero workflows: (1) search/query/retrieve references from the user's Zotero library and brainstorm from Zotero evidence, including ZOTseek semantic search, or (2) edit Word DOCX text and add selected Zotero items as live citation fields. Prefer structured Pyzotero CLI (`zot`) for low-context exact retrieval; use ZOTseek MCP for conceptual semantic discovery after live tool discovery. Zotero library create/update/delete actions are secondary and should only be done when explicitly requested. Trigger on Zotero, Pyzotero, zot, ZOTseek, semantic library search, Zotero MCP, Word/DOCX Zotero citations, literature searches within Zotero, Zotero reference review, paper brainstorming from a Zotero library, metadata, collections, tags, recent items, attachments/notes, full-text retrieval, or Zotero setup."
---

# Zotero Use

## Update Check

On the first invocation in each task, run `python3 scripts/check_updates.py`. The command is silent unless a randomized 14-17 day check is due and GitHub reports a newer version. Surface a non-empty update notice once, then continue the user's task. Never auto-update. Respect `ZOTERO_USE_UPDATE_CHECK=0`.

## Routing

1. Primary workflow A: search/query/retrieve Zotero references and brainstorm from Zotero evidence.
2. Primary workflow B: edit Word DOCX text and add selected Zotero items as live citation fields.
3. Prefer Pyzotero CLI (`zot`) for exact item search, browse, metadata, attachments, and full-text retrieval.
4. Use the local ZOTseek MCP endpoint for conceptual or passage-level semantic discovery. On its first use in each task, discover every live tool and schema with `python3 scripts/zotseek_mcp.py tools` (or native MCP discovery); do not assume hard-coded tool names.
5. Do not add MCP config to `.agents`, Codex skill metadata, or agent config by default.
6. Warn that adding MCP tools to an agent session consumes context/tool-list budget.
7. Treat Zotero library create/update/delete as secondary; do not modify the Zotero library unless the user explicitly asks.
8. Avoid direct local API wrappers and raw SQLite in this skill; use Pyzotero CLI instead.
9. For Word work, use the agent's available Word/DOCX editing skill or document tooling. Do not install a separate DOCX-editing dependency solely for Zotero citation insertion.
10. Validate edited DOCX files with `scripts/validate_zotero_docx.py`, which is read-only and uses only the Python standard library. Do not require `unzip`, `xmllint`, `rg`, `qlmanage`, LibreOffice, or rendering for narrow citation-field validation.
11. Before first use or when troubleshooting setup, run `python3 scripts/selftest.py`. Use `--strict` when `zot` and a working local Zotero read connection are required, and `--require-zotseek` when semantic search is required.
12. For received or collaborative DOCX files, inventory citation library namespaces and embedded `itemData` before editing. Preserve foreign fields unchanged; never combine a key from one library with another library's URI namespace.
13. Treat received Zotero DOCX files as preservation-critical. Keep the original untouched, never open them through the OS default app, never trigger Zotero Refresh automatically, and validate the edited copy against the original with `--preserve-baseline-citations`.

## Work Pattern

1. Search broadly, then narrow by title, creator, collection, tag, item type, or year.
2. For conceptual searches, discover ZOTseek's live tools, check index status when offered, run semantic/hybrid search, then confirm shortlisted item metadata with `zot`.
3. Inspect metadata for shortlisted parent bibliographic items; avoid citing attachment keys.
4. For a single selected item, check children/attachments and report whether a PDF is available.
5. For brainstorming/review, use the abstract plus PDF/full text when available; if only metadata/abstract was reviewed, say so.
6. For Word work, let the available document skill read, edit, and preserve the DOCX; supply the Zotero field semantics and validate the result with the bundled validator.
7. When adding to a received document, use the URI returned for each selected item from the current Zotero library; mixed personal/group namespaces are valid.
8. Report Zotero item keys with conclusions and citation-placement suggestions.
9. Distinguish Zotero evidence from external knowledge or inference.

## Lazy References

- Pyzotero CLI install, local mode, profiles, and command examples: `references/pyzotero-cli.md`
- Search/query/retrieve/brainstorm from Zotero references: `references/search-retrieve-brainstorm.md`
- ZOTseek MCP semantic search and live tool discovery: `references/zotseek-mcp.md`
- Adding Zotero citation fields to Word DOCX files: `references/word-docx-citations.md`
- Dependency-free DOCX/OOXML and Zotero-field validator: `scripts/validate_zotero_docx.py`
- Dependency and Zotero readiness self-test: `scripts/selftest.py`
- Non-blocking, jittered GitHub version check: `scripts/check_updates.py`
- Zotero MCP server setup, context warning, and MCP tool usage: `references/zotero-mcp.md`
- Troubleshooting and common checks: `references/setup-troubleshooting.md`

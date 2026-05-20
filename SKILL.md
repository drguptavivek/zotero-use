---
name: zotero-use
description: "Use when Codex needs either of the two primary Zotero workflows: (1) search/query/retrieve references from the user's Zotero library and brainstorm from Zotero evidence, or (2) edit Word DOCX text and add selected Zotero items as live citation fields. Prefer structured Pyzotero CLI (`zot`) for low-context terminal workflows; use Zotero MCP tools only when already available or explicitly requested. Zotero library create/update/delete actions are secondary and should only be done when explicitly requested. Trigger on Zotero, Pyzotero, zot, Zotero MCP, Word/DOCX Zotero citations, literature searches, reference review, paper brainstorming, metadata, collections, tags, recent items, attachments/notes, full-text retrieval, or Zotero setup."
---

# Zotero Use

## Routing

1. Primary workflow A: search/query/retrieve Zotero references and brainstorm from Zotero evidence.
2. Primary workflow B: edit Word DOCX text and add selected Zotero items as live citation fields.
3. Prefer Pyzotero CLI (`zot`) for library search/browse/metadata because it is structured and avoids MCP tool-schema context cost.
4. Use Zotero MCP tools only when they are already active or the user explicitly prefers MCP.
5. Do not add MCP config to `.agents`, Codex skill metadata, or agent config by default.
6. Warn that adding MCP tools to an agent session consumes context/tool-list budget.
7. Treat Zotero library create/update/delete as secondary; do not modify the Zotero library unless the user explicitly asks.
8. Avoid direct local API wrappers and raw SQLite in this skill; use Pyzotero CLI instead.

## Work Pattern

1. Search broadly, then narrow by title, creator, collection, tag, item type, or year.
2. Inspect metadata for shortlisted parent bibliographic items; avoid citing attachment keys.
3. For a single selected item, check children/attachments and report whether a PDF is available.
4. For brainstorming/review, use the abstract plus PDF/full text when available; if only metadata/abstract was reviewed, say so.
5. For Word work, edit the text and add live Zotero citation fields only in a git-tracked DOCX workspace.
6. Report Zotero item keys with conclusions and citation-placement suggestions.
7. Distinguish Zotero evidence from external knowledge or inference.

## Lazy References

- Pyzotero CLI install, local mode, profiles, and command examples: `references/pyzotero-cli.md`
- Search/query/retrieve/brainstorm from Zotero references: `references/search-retrieve-brainstorm.md`
- Adding Zotero citation fields to Word DOCX files: `references/word-docx-citations.md`
- Zotero MCP server setup, context warning, and MCP tool usage: `references/zotero-mcp.md`
- Verified local examples on this machine: `references/verified-local-examples.md`
- Troubleshooting and common checks: `references/setup-troubleshooting.md`

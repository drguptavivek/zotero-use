# zotero-use

This is an agent skill for my Zotero workflow. It is written for any coding/research agent that can load local skills and follow file-based instructions.

Primary use:

- search/query/retrieve references from my Zotero library
- review specific references using metadata, abstract, PDF/full text when available
- brainstorm from Zotero evidence in the current writing context
- edit Word `.docx` text and add selected Zotero references as live Zotero citation fields

The default path is token-light: prefer the structured Pyzotero CLI command `zot`.

Credit: this workflow is mainly built around `pyzotero-cli` by Chris Carroll Smith:
https://github.com/chriscarrollsmith/pyzotero-cli

MCP guidance is included, but not as the default. Adding MCP tools to an agent session consumes context/tool-list budget, so the skill recommends running Zotero/Pyzotero locally and using MCP only when explicitly preferred.

Zotero library edit/update/delete actions are secondary. The main intent is search, retrieve, think with the evidence, and cite into Word documents.

Install for agents that read from `~/.agents/skills`:

```bash
git clone https://github.com/drguptavivek/zotero-use.git ~/.agents/skills/zotero-use
```

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

## Install

For agents that read from `~/.agents/skills`:

```bash
git clone https://github.com/drguptavivek/zotero-use.git ~/.agents/skills/zotero-use
```

For Codex, ask the agent:

```text
Install the skill from drguptavivek/zotero-use
```

or clone it into the active Codex skills directory used on your machine.

For Claude-style local skills:

```bash
git clone https://github.com/drguptavivek/zotero-use.git ~/.claude/skills/zotero-use
```

For project-local Claude skills:

```bash
mkdir -p .claude/skills
git clone https://github.com/drguptavivek/zotero-use.git .claude/skills/zotero-use
```

For project-local Gemini skills:

```bash
mkdir -p .gemini/skills
git clone https://github.com/drguptavivek/zotero-use.git .gemini/skills/zotero-use
```

For Gemini or other agents, use the same pattern: clone this repo into the agent's local skills directory and restart the agent so it reloads available skills.

Marketplace/registry entry: point the skill installer to this GitHub repo. The skill root is the repository root, and the entrypoint is `SKILL.md`.

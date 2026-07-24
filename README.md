# zotero-use

[![skills.sh](https://skills.sh/b/drguptavivek/agent-skills)](https://skills.sh/drguptavivek/agent-skills)

This is an agent skill for my Zotero workflow. It is written for any coding/research agent that can load local skills and follow file-based instructions.

Primary use:

- search/query/retrieve references from my Zotero library
- semantically search the locally indexed library through ZOTseek MCP
- review specific references using metadata, abstract, PDF/full text when available
- brainstorm from Zotero evidence in the current writing context
- edit Word `.docx` text and add selected Zotero references as live Zotero citation fields

Use the structured Pyzotero CLI command `zot` for exact retrieval and ZOTseek MCP for conceptual or passage-level semantic discovery.

Credit: this workflow is mainly built around `pyzotero-cli` by Chris Carroll Smith:
https://github.com/chriscarrollsmith/pyzotero-cli

ZOTseek MCP is the optional semantic-discovery path. Generic Zotero MCP guidance is also included, but it is not the default for exact retrieval: adding persistent MCP tools to an agent session consumes context/tool-list budget, while the bundled ZOTseek client discovers tools only when needed.

Zotero library edit/update/delete actions are secondary. The main intent is search, retrieve, think with the evidence, and cite into Word documents.

## Self-Test

After installation, check Python, the bundled DOCX validator, `zot`, optional `uv`/`uvx`, Zotero MCP commands, ZOTseek MCP tool discovery, profile configuration, and read-only local Zotero access:

```bash
python3 scripts/selftest.py
```

Use `--strict` to require both `zot` and a successful local Zotero read. Use `--require-zotseek` to require successful live tool discovery at `http://localhost:23119/zotseek/mcp`. The self-test installs nothing and does not print library contents or secret values.

Before the first semantic search in a task, enumerate the live ZOTseek tools and schemas:

```bash
python3 scripts/zotseek_mcp.py tools
```

The client discovers the current tools before every call instead of relying on a fixed tool list. See `references/zotseek-mcp.md` for generic calls and endpoint override instructions.

## Zotero Setup

For local Zotero use, Zotero must allow local applications to talk to it:

Zotero > Settings > Advanced > Allow other applications on this computer to communicate with Zotero

Keep Zotero open when using local search/retrieve workflows.

For web-based Zotero use, generate an API key from your Zotero account:

https://www.zotero.org/settings/keys

You will need:

- the Zotero API key
- your Zotero user ID for a personal library, or the group ID for a group library
- whether the library is `user` or `group`

Configure these through `zot`:

```bash
zot configure setup
```

Use web-based setup when the local Zotero desktop app is not available, or when an agent needs access to an online Zotero library rather than the running desktop client.

## Install with the Skills CLI

Install from the curated [`drguptavivek/agent-skills`](https://github.com/drguptavivek/agent-skills) catalog using the open [`vercel-labs/skills`](https://github.com/vercel-labs/skills) CLI:

```bash
npx skills add drguptavivek/agent-skills --skill zotero-use
```

Install globally for a specific supported agent:

```bash
npx skills add drguptavivek/agent-skills --skill zotero-use --global --agent codex --yes
npx skills add drguptavivek/agent-skills --skill zotero-use --global --agent claude-code --yes
```

List the skill without installing it:

```bash
npx skills add drguptavivek/agent-skills --list
```

To install directly from this standalone repository instead:

```bash
npx skills add drguptavivek/zotero-use
```

This repository remains the canonical source for the skill; the curated catalog mirrors it automatically.

## Manual Install

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

After a manual installation, restart the agent so it reloads available skills.

# Changelog

All notable changes to `zotero-use` are recorded here using Keep a Changelog categories.

## [Unreleased]

## [2.0.0] - 2026-07-24

### Added

- Non-blocking update checker that compares the installed `VERSION` with GitHub and schedules successful checks with randomized 14-17 day jitter.
- Dependency-free environment self-test covering Python, `zot`, local Zotero access, profiles, optional integrations, and ZOTseek MCP discovery.
- Dependency-free DOCX/OOXML validator for Zotero citation fields, including field counts, item assertions, unique citation IDs, `noteIndex`, library namespaces, and embedded `itemData` coverage.
- ZOTseek MCP semantic search with live tool and schema discovery before every call.
- Permanent validator regression tests under `tests/`.

### Changed

- Delegate Word reading and editing to the agent's existing document tooling while keeping Zotero-specific field semantics in this skill.
- Keep synthetic citation JSON minimal: Zotero Refresh generates cached `formattedCitation`, `plainCitation`, and full `itemData`.
- Preserve foreign citation URIs and keys in received documents; use each newly selected item's own resolved Zotero URI instead of copying a document-wide namespace.
- Treat mixed personal and group-library namespaces as valid collaborative-document state.
- Require received Zotero DOCX files to remain untouched while edits are made to a separate copy; prohibit default-app launching and automatic Refresh.

### Security

- Require a recoverable copy and explicit warning before refreshing received citations that lack embedded metadata and cannot be resolved in the current Zotero libraries.
- Add baseline-preservation validation that fails if any original citation ID disappears or its item URI set changes.
- Ignore generated `test-artifacts/` so manual DOCX fixtures are not accidentally committed.

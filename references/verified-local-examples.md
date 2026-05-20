# Verified Local Examples

Verified on this machine on 2026-05-20.

State:

- `uv tool list` shows `pyzotero-cli v1.0.0`.
- The shell command is `zot`.
- `uv tool list` also shows `zotero-mcp-server v0.3.0`.
- `zotero-mcp-server` exposes `zotero-mcp`, not `zotero-cli`.
- Zotero local HTTP API is enabled and verified through Pyzotero CLI local mode.

Search example:

```bash
zot --local --library-id 0 --library-type user items list --query "glaucoma" --qmode everything --limit 3 --output table
```

Verified returned examples:

- `KR4W2Z67`: Rapid Assessment of Avoidable Blindness in Kunming, China
- `AUZMPZPA`: Wu - 2008 - Ophthalmology - Rapid Assessment of Avoidable.pdf
- `J2T3DQTF`: Prevalence and causes of vision loss in Central and South Asia: 1990-2010

Metadata example:

```bash
zot --local --library-id 0 --library-type user items get QUDEVEEJ --output table
```

Verified returned:

- `QUDEVEEJ`
- Title: Health Economic Implications of Artificial Intelligence Implementation for Ophthalmology in Australia: A Systematic Review
- Creator: Pietris et al.
- Date: 11/2022

Collection example:

```bash
zot --local --library-id 0 --library-type user collections list --top --limit 3 --output table
```

Verified returned examples:

- `YV7J83VK`: 00000 - AI DL ML
- `5TAII96D`: 0000 - Global Burden
- `STYNQ4RV`: 0000 - Methods

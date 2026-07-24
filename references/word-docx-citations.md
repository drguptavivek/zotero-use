# Word DOCX Zotero Citations

Use this reference when adding selected Zotero items to an existing `.docx` as live Zotero fields.

## Responsibility Boundary

- Use the agent's available Word/DOCX editing skill or document tooling to read the document, choose citation locations, edit OOXML, preserve formatting, and save the result.
- Use this skill only for Zotero item selection, citation-field semantics, and Zotero-specific validation.
- Do not install `python-docx`, `lxml`, or another DOCX-editing dependency solely for this workflow.
- Do not introduce a separate placeholder or citation-insertion script.

## Output Safety

- Establish a recoverable output strategy before editing.
- For a tracked DOCX, inspect its git status and preserve unrelated changes.
- For an untracked DOCX or a file outside a repository, create `<stem>-zotero-cited.docx` by default. Overwrite the input only when explicitly requested.
- Verify that input and output resolve to different paths and report both paths.

## Zotero Field Rules

- Cite parent bibliographic item keys, not attachment keys.
- Generate a unique `citationID` for every field insertion location.
- When the same item is cited at several locations, create a separate field and unique `citationID` at each location.
- When several items are cited at one location, create one field containing several `citationItems`. Do not create adjacent fields unless the user explicitly wants separate citations.
- Use the local item URI namespace already present in the document, or obtain the local user key before editing:

```text
http://zotero.org/users/local/<LOCAL_USER_KEY>/items/<ITEM_KEY>
```

## Minimal Citation JSON

Use this synthetic shape and supply the intended visible result text:

```json
{
  "citationID": "agent-unique-field-id",
  "properties": {
    "formattedCitation": "(Chawla et al. 2025)",
    "plainCitation": "(Chawla et al. 2025)",
    "noteIndex": 0
  },
  "citationItems": [
    {
      "id": "ABCD1234",
      "uris": [
        "http://zotero.org/users/local/LOCAL_USER_KEY/items/ABCD1234"
      ]
    }
  ],
  "schema": "https://github.com/citation-style-language/schema/raw/master/csl-citation.json"
}
```

Use this field instruction prefix:

```text
 ADDIN ZOTERO_ITEM CSL_CITATION <JSON>
```

Insert the normal Word complex-field sequence:

1. `w:fldChar w:fldCharType="begin"`
2. `w:instrText xml:space="preserve"` containing the instruction
3. `w:fldChar w:fldCharType="separate"`
4. A visible result run
5. `w:fldChar w:fldCharType="end"`

Preserve the document's namespace prefixes and surrounding run formatting. Avoid full XML rewrites that rename namespaces.

## Dependency-Free Validation

Run the bundled read-only validator with any available Python 3 interpreter. It uses only the standard library and does not render or modify the document:

```bash
python3 scripts/validate_zotero_docx.py manuscript-zotero-cited.docx \
  --minimum-fields 1
```

Compare an edited document with its original and verify the intended insertions:

```bash
python3 scripts/validate_zotero_docx.py manuscript-zotero-cited.docx \
  --baseline manuscript.docx \
  --expected-increase 2 \
  --expect-item-key ABCD1234 \
  --expect-item-key EFGH5678
```

The validator checks:

- ZIP integrity, unsafe or duplicate part names, and required DOCX parts
- XML well-formedness for every XML and relationships part
- complete begin/separate/end Zotero complex fields
- parseable citation JSON with `citationID`, `properties`, `citationItems`, item URIs, and schema
- unique `citationID` values
- optional baseline count increases, exact counts, item keys, citation IDs, and visible text

Use `--json` for machine-readable output. If Python 3 is unavailable, use the structural validation provided by the host document skill; do not install dependencies solely for validation.

## Word Refresh and Handoff

- The user must open the DOCX in Word with Zotero installed and run Zotero Refresh. Zotero should hydrate the minimal fields with internal IDs, user URIs, and full `itemData`.
- An existing live Zotero bibliography should update after refresh.
- If no bibliography field exists, ask whether the user wants a live bibliography field or plain reference text.
- Do not treat the document as final static output until Zotero Refresh succeeds.
- Report the output path, inserted-field count, cited item keys, and validation result.

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
- Use the URI belonging to the exact selected item. Obtain it from the current Zotero library or construct it only after verifying the item's user, local-user, or group-library identity:

```text
http://zotero.org/users/<USER_ID>/items/<ITEM_KEY>
http://zotero.org/users/local/<LOCAL_USER_KEY>/items/<ITEM_KEY>
http://zotero.org/groups/<GROUP_ID>/items/<ITEM_KEY>
```

- Do not copy a document-wide URI namespace onto new item keys. Zotero item keys are library-scoped.
- Preserve all existing citation IDs, item IDs, URIs, and embedded `itemData` unless the user explicitly requests citation replacement.

## Received And Collaborative Documents

Before editing, run the validator and inspect `portability.libraryNamespaces`, `itemsWithEmbeddedData`, and `itemsWithoutEmbeddedData`.

- Keep the received file untouched. Create a separate output copy before any edit.
- Do not open a Zotero DOCX through the operating system's default application. Pages and incompatible word-processor paths can destroy active fields. If interactive verification is explicitly requested, open the copy specifically in Microsoft Word with the Zotero plugin.
- Do not trigger Zotero Refresh automatically. Audit first; let the user decide whether to refresh after reviewing foreign/unresolved citations.
- Treat multiple personal or group-library namespaces as valid. Do not normalize them.
- An existing foreign citation with embedded `itemData` can remain usable as an orphaned citation within that document. Leave its field data unchanged when editing elsewhere.
- If the sender says the document contains live Zotero citations but the baseline validator finds none, stop. Do not edit or refresh because the fields may already be broken or stored in an unsupported form.
- If a foreign citation has no embedded `itemData` and its URI is not resolvable through the current Zotero libraries, create a copy and warn the user before Zotero Refresh. Do not claim it is portable.
- If the same publication exists in the current library under another key, do not auto-match or rewrite it by title, DOI, or item key. Replace it only through an explicit citation-relinking workflow.
- Add new citations using the selected items' own URIs. A document may legitimately contain citations from the sender's library, the recipient's library, and shared group libraries.

After editing, prove that every baseline citation survived before handoff:

```bash
python3 scripts/validate_zotero_docx.py received-zotero-cited.docx \
  --baseline received.docx \
  --preserve-baseline-citations \
  --expected-increase 2
```

`--preserve-baseline-citations` fails if any original citation ID disappears or if its item URI set changes. Do not deliver an edited received document when this check fails.

## Minimal Citation JSON

Use this synthetic shape for a citation in the main document text:

```json
{
  "citationID": "agent-unique-field-id",
  "properties": {
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

`noteIndex` is `0` for main-text citations. For a citation in a footnote or endnote, use its actual positive note number. This gives the CSL processor the context needed by note styles.

Do not synthesize `formattedCitation` or `plainCitation`. They are cached renderings that Zotero creates during Refresh, not bibliographic inputs. The document-editing skill must insert the intended provisional text separately as the visible Word field result; Zotero Refresh will replace it according to the document's active citation style.

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
- parseable citation JSON with `citationID`, a valid `properties.noteIndex`, `citationItems`, item URIs, and schema
- unique `citationID` values
- personal, local-user, and group-library URI namespaces plus embedded `itemData` coverage
- optional baseline count increases, exact counts, item keys, citation IDs, and visible text
- preservation of every baseline citation ID and its item URIs when requested

Use `--json` for machine-readable output. If Python 3 is unavailable, use the structural validation provided by the host document skill; do not install dependencies solely for validation.

## Word Refresh and Handoff

- The user must open the DOCX in Word with Zotero installed and run Zotero Refresh. Zotero should hydrate the minimal fields with internal IDs, user URIs, full `itemData`, and cached formatted/plain citation text.
- An existing live Zotero bibliography should update after refresh.
- If no bibliography field exists, ask whether the user wants a live bibliography field or plain reference text.
- Do not treat the document as final static output until Zotero Refresh succeeds.
- Report the output path, inserted-field count, cited item keys, and validation result.

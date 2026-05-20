# Word DOCX Zotero Citations

Use this when adding Zotero references to an existing `.docx` with live Zotero fields.

## Proven Local Workflow

This workflow was tested on `sample.docx` on 2026-05-20:

- Insert a minimal Word field with `ADDIN ZOTERO_ITEM CSL_CITATION`.
- Include only `citationID`, `properties`, `citationItems.id`, `citationItems.uris`, and `schema`.
- Do not embed huge `itemData` manually.
- Open in Word and run Zotero Refresh.
- Zotero resolves the local item URI and hydrates the field with full `itemData`.

This is useful because it avoids generating large CSL JSON manually while still creating a field Zotero can refresh.

## Preconditions

- Work on a git-tracked DOCX in a git repository. Use git history for restore/version management instead of creating multiple ad hoc DOCX copies.
- Before editing, run `git status --short -- <file.docx>` and preserve any unrelated user changes.
- The DOCX already contains Zotero fields, or you know the local Zotero URI namespace.
- The user can open the DOCX in Word with Zotero installed and click Zotero Refresh.
- Zotero local API is enabled and the item exists in the local Zotero library.

Get the local namespace from existing fields:

```text
http://zotero.org/users/local/<LOCAL_USER_KEY>/items/<ITEM_KEY>
```

Example from this machine:

```text
http://zotero.org/users/local/BszOcoDo/items/FJRYBQGQ
```

## Search For The Reference

Use Pyzotero CLI:

```bash
zot --local --library-id 0 --library-type user items list --query "artificial intelligence ophthalmology" --qmode everything --filter-item-type journalArticle --limit 10 --output table
zot --local --library-id 0 --library-type user items get FJRYBQGQ --output table
```

Prefer a parent bibliographic item key, not an attachment key.

## Minimal Citation JSON

Use this shape:

```json
{
  "citationID": "codexFJRYBQGQ",
  "properties": {
    "formattedCitation": "(Chawla et al. 2025)",
    "plainCitation": "(Chawla et al. 2025)",
    "noteIndex": 0
  },
  "citationItems": [
    {
      "id": "FJRYBQGQ",
      "uris": [
        "http://zotero.org/users/local/BszOcoDo/items/FJRYBQGQ"
      ]
    }
  ],
  "schema": "https://github.com/citation-style-language/schema/raw/master/csl-citation.json"
}
```

Field instruction prefix:

```text
 ADDIN ZOTERO_ITEM CSL_CITATION <JSON>
```

Visible field result should be the formatted citation, for example:

```text
(Chawla et al. 2025)
```

## DOCX Editing Rules

- Preserve the original `document.xml` namespace declarations and prefixes.
- Avoid full XML rewrites that rename namespaces, such as changing `mc:` to `ns1:`; Word may report unreadable content.
- Prefer narrow string-level insertion or a namespace-preserving OOXML tool.
- For narrow Zotero citation insertions, do not load or run a full document rendering workflow by default.
- Explicitly do not run `soffice`, LibreOffice PDF conversion, PDF2image rendering, or `render_docx.py` for routine Zotero field insertion.
- Insert a normal Word field sequence:
  - `w:fldChar w:fldCharType="begin"`
  - `w:instrText xml:space="preserve"` containing the Zotero instruction
  - `w:fldChar w:fldCharType="separate"`
  - visible result text run
  - `w:fldChar w:fldCharType="end"`
- Use the surrounding run formatting so the citation matches the paragraph.

## Narrow OOXML Validation

For small Zotero citation edits, prefer these checks over LibreOffice/PDF rendering:

```bash
unzip -t file.docx
unzip -p file.docx word/document.xml | xmllint --noout -
unzip -p file.docx word/document.xml | rg -o "ADDIN ZOTERO_ITEM CSL_CITATION" | wc -l
unzip -p file.docx word/document.xml | rg "citationID|http://zotero.org/users/.+/items/|FormattedCitation|plainCitation"
```

Also verify:

- Zotero field count increased by the expected number.
- Each inserted field has the intended `citationID`, visible result text, and item URI.
- Combined citations are one field with multiple `citationItems`, not multiple adjacent fields unless the user specifically wants separate citations.
- `citationItems.id` should be the Zotero item key for a minimal local field; Zotero can hydrate full internal IDs and `itemData` after Word Zotero Refresh.

Use Quick Look or another lightweight preview only when a visual sanity check is useful:

```bash
qlmanage -t -s 1600 -o /tmp/docx-preview file.docx
```

Reserve `soffice`, LibreOffice PDF conversion, PDF2image rendering, and `render_docx.py` for substantial layout edits, tables/figures, final static DOCX delivery, suspected unreadable-document issues, or when the user explicitly asks for full visual QA.

## Word Refresh

After refresh, Zotero should expand the field with:

- numeric internal `id`
- local URI
- user URI
- full `itemData`

## Bibliography

If the document already has a Zotero bibliography field, Zotero Refresh should update it after resolving the new citation.

If no bibliography field exists, ask the user whether they want a live Zotero bibliography field or plain reference text.

## Warnings

- This is a Word/Zotero-refresh-dependent workflow.
- Do not use it for final static DOCX output unless the user can refresh in Word.
- Use git for rollback. Do not pollute the workspace with multiple experimental DOCX copies unless the user explicitly asks for a separate copy.
- Validate field counts before and after insertion.

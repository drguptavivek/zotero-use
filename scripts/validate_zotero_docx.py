#!/usr/bin/env python3
"""Validate DOCX/OOXML structure and live Zotero citation fields.

This script is read-only and uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree


ZOTERO_PREFIX = "ADDIN ZOTERO_ITEM CSL_CITATION"
REQUIRED_PARTS = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def attribute(element: ElementTree.Element, name: str) -> str | None:
    for key, value in element.attrib.items():
        if local_name(key) == name:
            return value
    return None


def validate_citation_data(
    data: Any, part: str, visible_text: str, errors: list[str]
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "part": part,
        "citationID": None,
        "noteIndex": None,
        "itemCount": 0,
        "itemKeys": [],
        "itemURIs": [],
        "visibleText": visible_text,
    }
    if not isinstance(data, dict):
        errors.append(f"{part}: citation JSON must be an object")
        return result

    citation_id = data.get("citationID")
    if not isinstance(citation_id, str) or not citation_id.strip():
        errors.append(f"{part}: citationID is missing or empty")
    else:
        result["citationID"] = citation_id

    properties = data.get("properties")
    if not isinstance(properties, dict):
        errors.append(f"{part}: properties must be an object")
    else:
        note_index = properties.get("noteIndex")
        if (
            isinstance(note_index, bool)
            or not isinstance(note_index, int)
            or note_index < 0
        ):
            errors.append(
                f"{part}: properties.noteIndex must be a non-negative integer"
            )
        else:
            result["noteIndex"] = note_index

    items = data.get("citationItems")
    if not isinstance(items, list) or not items:
        errors.append(f"{part}: citationItems must be a non-empty array")
        return result
    result["itemCount"] = len(items)

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"{part}: citationItems[{index}] must be an object")
            continue
        item_id = item.get("id")
        if not isinstance(item_id, (str, int)) or str(item_id).strip() == "":
            errors.append(f"{part}: citationItems[{index}].id is missing")
        else:
            result["itemKeys"].append(str(item_id))

        uris = item.get("uris")
        if not isinstance(uris, list) or not uris or not all(
            isinstance(uri, str) and uri for uri in uris
        ):
            errors.append(
                f"{part}: citationItems[{index}].uris must be a non-empty string array"
            )
        else:
            result["itemURIs"].extend(uris)

    schema = data.get("schema")
    if not isinstance(schema, str) or not schema:
        errors.append(f"{part}: schema is missing")
    return result


def extract_zotero_fields(
    xml_bytes: bytes, part: str, errors: list[str]
) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as exc:
        errors.append(f"{part}: invalid XML: {exc}")
        return []

    fields: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []

    for element in root.iter():
        name = local_name(element.tag)
        if name == "fldChar":
            field_type = attribute(element, "fldCharType")
            if field_type == "begin":
                stack.append(
                    {"instruction": [], "visible": [], "hasSeparate": False}
                )
            elif field_type == "separate" and stack:
                stack[-1]["hasSeparate"] = True
            elif field_type == "end" and stack:
                field = stack.pop()
                instruction = "".join(field["instruction"]).strip()
                if ZOTERO_PREFIX not in instruction:
                    continue
                if not field["hasSeparate"]:
                    errors.append(f"{part}: Zotero field has no separate marker")
                json_text = instruction.split(ZOTERO_PREFIX, 1)[1].strip()
                try:
                    citation_data = json.loads(json_text)
                except json.JSONDecodeError as exc:
                    errors.append(f"{part}: invalid Zotero citation JSON: {exc}")
                    continue
                fields.append(
                    validate_citation_data(
                        citation_data,
                        part,
                        "".join(field["visible"]),
                        errors,
                    )
                )
        elif name == "instrText" and stack:
            stack[-1]["instruction"].append(element.text or "")
        elif name == "t" and stack and stack[-1]["hasSeparate"]:
            stack[-1]["visible"].append(element.text or "")

    raw_count = xml_bytes.count(ZOTERO_PREFIX.encode("ascii"))
    if raw_count != len(fields):
        errors.append(
            f"{part}: found {raw_count} Zotero instruction(s) but parsed "
            f"{len(fields)} complete Zotero field(s)"
        )
    return fields


def inspect_docx(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "xmlParts": 0,
        "zoteroFields": [],
        "errors": [],
    }
    errors: list[str] = result["errors"]

    if not path.is_file():
        errors.append("file does not exist or is not a regular file")
        return result

    try:
        with zipfile.ZipFile(path) as package:
            names = package.namelist()
            if len(names) != len(set(names)):
                errors.append("ZIP package contains duplicate part names")

            for name in names:
                candidate = PurePosixPath(name)
                if candidate.is_absolute() or ".." in candidate.parts:
                    errors.append(f"unsafe ZIP part path: {name}")

            missing = sorted(REQUIRED_PARTS.difference(names))
            if missing:
                errors.append(f"missing required OOXML part(s): {', '.join(missing)}")

            bad_member = package.testzip()
            if bad_member:
                errors.append(f"ZIP CRC check failed for: {bad_member}")

            for name in names:
                if not (name.endswith(".xml") or name.endswith(".rels")):
                    continue
                try:
                    xml_bytes = package.read(name)
                except (KeyError, RuntimeError, zipfile.BadZipFile) as exc:
                    errors.append(f"{name}: could not read part: {exc}")
                    continue
                result["xmlParts"] += 1
                try:
                    ElementTree.fromstring(xml_bytes)
                except ElementTree.ParseError as exc:
                    errors.append(f"{name}: invalid XML: {exc}")
                    continue
                if name.startswith("word/") and name.endswith(".xml"):
                    result["zoteroFields"].extend(
                        extract_zotero_fields(xml_bytes, name, errors)
                    )
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"not a readable DOCX/ZIP package: {exc}")

    citation_ids: list[str] = [
        field["citationID"]
        for field in result["zoteroFields"]
        if field["citationID"] is not None
    ]
    duplicates = sorted({value for value in citation_ids if citation_ids.count(value) > 1})
    if duplicates:
        errors.append(f"duplicate citationID value(s): {', '.join(duplicates)}")
    return result


def apply_expectations(
    result: dict[str, Any], baseline: dict[str, Any] | None, args: argparse.Namespace
) -> None:
    errors: list[str] = result["errors"]
    fields: list[dict[str, Any]] = result["zoteroFields"]
    count = len(fields)

    if args.minimum_fields is not None and count < args.minimum_fields:
        errors.append(f"expected at least {args.minimum_fields} Zotero field(s), found {count}")
    if args.expected_field_count is not None and count != args.expected_field_count:
        errors.append(
            f"expected exactly {args.expected_field_count} Zotero field(s), found {count}"
        )
    if args.expected_increase is not None:
        if baseline is None:
            errors.append("--expected-increase requires --baseline")
        else:
            increase = count - len(baseline["zoteroFields"])
            if increase != args.expected_increase:
                errors.append(
                    f"expected Zotero field count to increase by {args.expected_increase}, "
                    f"observed {increase}"
                )

    citation_ids = {field["citationID"] for field in fields}
    item_values = {
        value
        for field in fields
        for value in field["itemKeys"] + field["itemURIs"]
    }
    visible_text = "\n".join(field["visibleText"] for field in fields)

    for expected in args.expect_citation_id:
        if expected not in citation_ids:
            errors.append(f"expected citationID not found: {expected}")
    for expected in args.expect_item_key:
        if not any(
            value == expected or value.rstrip("/").endswith(f"/items/{expected}")
            for value in item_values
        ):
            errors.append(f"expected Zotero item key not found: {expected}")
    for expected in args.expect_visible_text:
        if expected not in visible_text:
            errors.append(f"expected visible citation text not found: {expected}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path, help="DOCX file to validate")
    parser.add_argument("--baseline", type=Path, help="Original DOCX for count comparison")
    parser.add_argument("--minimum-fields", type=int)
    parser.add_argument("--expected-field-count", type=int)
    parser.add_argument("--expected-increase", type=int)
    parser.add_argument("--expect-citation-id", action="append", default=[])
    parser.add_argument("--expect-item-key", action="append", default=[])
    parser.add_argument("--expect-visible-text", action="append", default=[])
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = inspect_docx(args.docx)
    baseline = inspect_docx(args.baseline) if args.baseline else None
    if baseline is not None and baseline["errors"]:
        result["errors"].extend(
            f"baseline: {message}" for message in baseline["errors"]
        )
    apply_expectations(result, baseline, args)

    if baseline is not None:
        result["baseline"] = {
            "path": baseline["path"],
            "zoteroFieldCount": len(baseline["zoteroFields"]),
            "fieldCountIncrease": len(result["zoteroFields"])
            - len(baseline["zoteroFields"]),
        }
    result["zoteroFieldCount"] = len(result["zoteroFields"])
    result["valid"] = not result["errors"]

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status = "OK" if result["valid"] else "INVALID"
        print(f"{status}: {result['path']}")
        print(f"XML/relationships parts parsed: {result['xmlParts']}")
        print(f"Zotero fields: {result['zoteroFieldCount']}")
        for field in result["zoteroFields"]:
            print(
                f"- {field['part']}: citationID={field['citationID']!r}; "
                f"items={field['itemCount']}; visible={field['visibleText']!r}"
            )
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

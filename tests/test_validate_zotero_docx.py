import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_zotero_docx.py"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def citation_field(
    citation_id, items, visible, namespace="users/local/OWNER", embedded_keys=()
):
    citation_items = []
    for key in items:
        item = {
            "id": key,
            "uris": [f"http://zotero.org/{namespace}/items/{key}"],
        }
        if key in embedded_keys:
            item["itemData"] = {"id": key, "type": "article-journal", "title": key}
        citation_items.append(item)
    data = {
        "citationID": citation_id,
        "properties": {"noteIndex": 0},
        "citationItems": citation_items,
        "schema": "https://github.com/citation-style-language/schema/raw/master/csl-citation.json",
    }
    instruction = " ADDIN ZOTERO_ITEM CSL_CITATION " + json.dumps(data)
    instruction = instruction.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve">{instruction}</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        f'<w:r><w:t>{visible}</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )


def make_docx(path, fields="", malformed=False):
    document = (
        f'<w:document xmlns:w="{W}"><w:body><w:p>{fields}</w:p>'
        "<w:sectPr/></w:body></w:document>"
    )
    if malformed:
        document = document[:-13]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        package.writestr(
            "_rels/.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        )
        package.writestr("word/document.xml", document)


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_validator(self, *args):
        return subprocess.run(
            [sys.executable, "-I", "-S", str(SCRIPT), *map(str, args)],
            text=True,
            capture_output=True,
        )

    def test_multiple_locations_and_combined_items(self):
        baseline = self.root / "baseline.docx"
        edited = self.root / "edited.docx"
        make_docx(baseline)
        make_docx(
            edited,
            citation_field("field-1", ["ABCD1234", "EFGH5678"], "(A; B)")
            + citation_field("field-2", ["IJKL9012"], "(C)"),
        )
        result = self.run_validator(
            edited,
            "--baseline",
            baseline,
            "--expected-increase",
            "2",
            "--expect-item-key",
            "ABCD1234",
            "--expect-item-key",
            "EFGH5678",
            "--expect-item-key",
            "IJKL9012",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["zoteroFieldCount"], 2)
        self.assertEqual(payload["portability"]["embeddedDataCoverage"], "none")

    def test_mixed_namespaces_and_item_data_are_reported(self):
        edited = self.root / "collaborative.docx"
        make_docx(
            edited,
            citation_field(
                "foreign-field",
                ["ABCD1234"],
                "(A)",
                namespace="users/111",
                embedded_keys=("ABCD1234",),
            )
            + citation_field(
                "group-field",
                ["EFGH5678"],
                "(B)",
                namespace="groups/222",
            ),
        )
        result = self.run_validator(edited, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        portability = json.loads(result.stdout)["portability"]
        self.assertEqual(portability["libraryNamespaces"], ["groups/222", "users/111"])
        self.assertTrue(portability["mixedLibraryNamespaces"])
        self.assertEqual(portability["itemsWithEmbeddedData"], 1)
        self.assertEqual(portability["itemsWithoutEmbeddedData"], 1)
        self.assertEqual(portability["embeddedDataCoverage"], "partial")

    def test_baseline_citations_must_survive(self):
        baseline = self.root / "received.docx"
        edited = self.root / "edited.docx"
        make_docx(
            baseline,
            citation_field("foreign-1", ["ABCD1234"], "(A)", "users/111")
            + citation_field("foreign-2", ["EFGH5678"], "(B)", "users/111"),
        )
        make_docx(
            edited,
            citation_field("foreign-1", ["ABCD1234"], "(A)", "users/111")
            + citation_field("new-local", ["IJKL9012"], "(C)", "users/222"),
        )
        result = self.run_validator(
            edited, "--baseline", baseline, "--preserve-baseline-citations"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("baseline citationID value(s) missing: foreign-2", result.stderr)

    def test_baseline_citations_can_survive_with_new_fields(self):
        baseline = self.root / "received.docx"
        edited = self.root / "edited.docx"
        original = citation_field(
            "foreign-1", ["ABCD1234"], "(A)", "users/111"
        )
        make_docx(baseline, original)
        make_docx(
            edited,
            original
            + citation_field("new-local", ["IJKL9012"], "(C)", "users/222"),
        )
        result = self.run_validator(
            edited,
            "--baseline",
            baseline,
            "--preserve-baseline-citations",
            "--expected-increase",
            "1",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        preservation = json.loads(result.stdout)["preservation"]
        self.assertTrue(preservation["passed"])
        self.assertEqual(preservation["preservedCitationCount"], 1)

    def test_baseline_citation_uri_cannot_be_rewritten(self):
        baseline = self.root / "received.docx"
        edited = self.root / "rewritten.docx"
        make_docx(
            baseline,
            citation_field("foreign-1", ["ABCD1234"], "(A)", "users/111"),
        )
        make_docx(
            edited,
            citation_field("foreign-1", ["ABCD1234"], "(A)", "users/222"),
        )
        result = self.run_validator(
            edited, "--baseline", baseline, "--preserve-baseline-citations"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "baseline citation item URI set changed for citationID value(s): foreign-1",
            result.stderr,
        )

    def test_empty_baseline_cannot_establish_preservation(self):
        baseline = self.root / "received.docx"
        edited = self.root / "edited.docx"
        make_docx(baseline)
        make_docx(
            edited,
            citation_field("new-local", ["ABCD1234"], "(A)", "users/222"),
        )
        result = self.run_validator(
            edited, "--baseline", baseline, "--preserve-baseline-citations"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "baseline contains no valid Zotero citation fields",
            result.stderr,
        )

    def test_duplicate_citation_id_fails(self):
        edited = self.root / "duplicate.docx"
        make_docx(
            edited,
            citation_field("same-id", ["ABCD1234"], "(A)")
            + citation_field("same-id", ["EFGH5678"], "(B)"),
        )
        result = self.run_validator(edited)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate citationID", result.stderr)

    def test_invalid_note_index_fails(self):
        edited = self.root / "invalid-note-index.docx"
        field = citation_field("field-1", ["ABCD1234"], "(A)")
        field = field.replace('\"noteIndex\": 0', '\"noteIndex\": -1')
        make_docx(edited, field)
        result = self.run_validator(edited)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("properties.noteIndex must be a non-negative integer", result.stderr)

    def test_malformed_xml_fails(self):
        edited = self.root / "malformed.docx"
        make_docx(edited, malformed=True)
        result = self.run_validator(edited)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid XML", result.stderr)


if __name__ == "__main__":
    unittest.main()

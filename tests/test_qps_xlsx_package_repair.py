"""Package repair regressions: native fidelity and unchanged cell/package bytes."""

from __future__ import annotations

import importlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
fixture_bytes = importlib.import_module("test_qps_xlsx_native_features").fixture_bytes
table_fixture_bytes = importlib.import_module(
    "test_qps_xlsx_native_features"
).table_fixture_bytes
engine = importlib.import_module("tools.qps_xlsx_package_repair")
native = importlib.import_module("tools.qps_xlsx_native_features")
compare_content = native.compare_content
compare_features = native.compare_features
digest = native.digest
evaluate_repair = native.evaluate_repair
snapshot_xlsx = native.snapshot_xlsx
repair_native_package = engine.repair_native_package


def mutate(raw, replacements=None, additions=None):
    buffer = io.BytesIO()
    replacements = replacements or {}
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(
        buffer, "w"
    ) as output:
        output.comment = source.comment
        for entry in source.infolist():
            value = source.read(entry.filename)
            for before, after in replacements.get(entry.filename, []):
                if before not in value:
                    raise AssertionError((entry.filename, before))
                value = value.replace(before, after)
            output.writestr(entry, value)
        for key, value in (additions or {}).items():
            output.writestr(key, value)
    return buffer.getvalue()


def call(source, candidate):
    return repair_native_package(
        source,
        candidate,
        expected_source_sha=digest(source),
        expected_candidate_sha=digest(candidate),
    )


def external_fixture():
    """Two different external books with an index-bound source defined name."""
    rel = native.REL.encode()
    return mutate(
        fixture_bytes(),
        {
            "xl/workbook.xml": [
                (
                    b"<definedNames>",
                    b'<externalReferences><externalReference r:id="ext1"/>'
                    b'<externalReference r:id="ext2"/></externalReferences>'
                    b'<definedNames><definedName name="ExternalValue">'
                    b"[1]Sheet1!$A$1</definedName>",
                )
            ],
            "xl/_rels/workbook.xml.rels": [
                (
                    b"</Relationships>",
                    b'<Relationship Id="ext1" Type="'
                    + rel
                    + b'/externalLink" Target="externalLinks/externalLink1.xml"/>'
                    b'<Relationship Id="ext2" Type="'
                    + rel
                    + b'/externalLink" Target="externalLinks/externalLink2.xml"/>'
                    b"</Relationships>",
                )
            ],
        },
        {
            "xl/externalLinks/externalLink1.xml": b'<externalLink book="A"/>',
            "xl/externalLinks/externalLink2.xml": b'<externalLink book="B"/>',
        },
    )


class PackageRepairTests(unittest.TestCase):
    def test_table_filter_loss_is_rejected_without_unsupported_restoration(self):
        source = table_fixture_bytes(criterion="Open")
        candidate = table_fixture_bytes(criterion="Closed")
        with self.assertRaisesRegex(ValueError, "NATIVE_TABLE_FILTERS_CHANGED"):
            call(source, candidate)

    def test_unchanged_table_filter_part_is_byte_preserved(self):
        source = table_fixture_bytes()
        final, receipt = call(source, source)
        with zipfile.ZipFile(io.BytesIO(source)) as before, zipfile.ZipFile(
            io.BytesIO(final)
        ) as after:
            self.assertEqual(
                before.read("xl/tables/table1.xml"), after.read("xl/tables/table1.xml")
            )
        self.assertEqual(receipt["remaining_native_losses"], [])

    def test_identical_ordered_external_bindings_preserved(self):
        source = external_fixture()
        final, receipt = call(source, source)
        self.assertEqual(receipt["external_reference_count"], 2)
        self.assertEqual(
            engine._external_reference_bindings(engine._parts(source)),
            engine._external_reference_bindings(engine._parts(final)),
        )
        self.assertEqual(receipt["remaining_native_losses"], [])
        self.assertEqual(receipt["content_losses"], [])

    def test_external_index_reorder_rejected_with_identical_link_parts(self):
        source = external_fixture()
        candidate = mutate(
            source,
            {
                "xl/workbook.xml": [
                    (
                        b'<externalReference r:id="ext1"/>'
                        b'<externalReference r:id="ext2"/>',
                        b'<externalReference r:id="ext2"/>'
                        b'<externalReference r:id="ext1"/>',
                    )
                ]
            },
        )
        # The old feature/content gate could not detect this binding loss.
        self.assertEqual(
            compare_features(snapshot_xlsx(source), snapshot_xlsx(candidate)), []
        )
        self.assertEqual(
            compare_content(snapshot_xlsx(source), snapshot_xlsx(candidate)), []
        )
        with self.assertRaisesRegex(
            ValueError, "UNSUPPORTED_EXTERNAL_REFERENCE_BINDING_CHANGE"
        ):
            call(source, candidate)

    def test_external_relationship_target_change_rejected(self):
        source = external_fixture()
        candidate = mutate(
            source,
            {
                "xl/_rels/workbook.xml.rels": [
                    (
                        b'Target="externalLinks/externalLink1.xml"',
                        b'Target="externalLinks/externalLink2.xml"',
                    )
                ]
            },
        )
        with self.assertRaisesRegex(
            ValueError, "UNSUPPORTED_EXTERNAL_REFERENCE_BINDING_CHANGE"
        ):
            call(source, candidate)

    def test_unresolved_or_unsupported_external_binding_rejected(self):
        source = external_fixture()
        cases = [
            (
                "xl/workbook.xml",
                b'<externalReference r:id="ext1"/>',
                b'<externalReference r:id="absent"/>',
            ),
            (
                "xl/_rels/workbook.xml.rels",
                b'Target="externalLinks/externalLink1.xml"',
                b'Target="externalLinks/externalLink1.xml" TargetMode="External"',
            ),
            (
                "xl/_rels/workbook.xml.rels",
                b'/externalLink" Target="externalLinks/externalLink1.xml"',
                b'/worksheet" Target="externalLinks/externalLink1.xml"',
            ),
        ]
        for part, before, after in cases:
            candidate = mutate(source, {part: [(before, after)]})
            with self.subTest(after=after), self.assertRaisesRegex(
                ValueError, "UNSUPPORTED_EXTERNAL_REFERENCE_BINDING"
            ):
                call(source, candidate)

    def test_duplicate_relationship_id_rejected_for_external_binding(self):
        source = external_fixture()
        candidate = mutate(
            source,
            {"xl/_rels/workbook.xml.rels": [(b'Id="ext2"', b'Id="ext1"')]},
        )
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_WORKBOOK_RELATIONSHIP"):
            call(source, candidate)

    def test_cli_refuses_input_alias_and_existing_output(self):
        raw = fixture_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, candidate = root / "source.xlsx", root / "candidate.xlsx"
            source.write_bytes(raw)
            candidate.write_bytes(raw)
            receipt = root / "receipt.json"
            for output in (source, root / "exists.xlsx"):
                if output != source:
                    output.write_bytes(b"sentinel")
                arguments = [
                    "package-repair",
                    "--source",
                    str(source),
                    "--candidate",
                    str(candidate),
                    "--expected-source-sha",
                    digest(raw),
                    "--expected-candidate-sha",
                    digest(raw),
                    "--trial-output",
                    str(output),
                    "--receipt",
                    str(receipt),
                ]
                with self.subTest(output=output.name), patch.object(
                    sys, "argv", arguments
                ):
                    with self.assertRaises((ValueError, FileExistsError)):
                        engine.main()
                self.assertEqual(source.read_bytes(), raw)
                self.assertEqual(candidate.read_bytes(), raw)
                self.assertFalse(receipt.exists())
                if output != source:
                    self.assertEqual(output.read_bytes(), b"sentinel")

    def test_corrupted_writer_cannot_change_cache_or_formula_attributes(self):
        original_repack = engine._repack
        raw = fixture_bytes()
        for before, after in [
            (b"<v>2</v>", b"<v>3</v>"),
            (b"<f>1+1</f>", b'<f aca="1">1+1</f>'),
        ]:

            def broken(candidate, parts):
                return mutate(
                    original_repack(candidate, parts),
                    {"xl/worksheets/sheet1.xml": [(before, after)]},
                )

            with self.subTest(after=after), patch.object(
                engine, "_repack", broken
            ), self.assertRaisesRegex(
                ValueError, "UNAUTHORIZED_XML_BYTES_CHANGED|REJECTED_SERIALIZED_LOSS"
            ):
                call(raw, raw)

    def test_corrupted_writer_cannot_modify_noncell_sheet_metadata(self):
        original_repack = engine._repack
        raw = fixture_bytes()

        def broken(candidate, parts):
            return mutate(
                original_repack(candidate, parts),
                {
                    "xl/worksheets/sheet1.xml": [
                        (b"</worksheet>", b'<dataValidations count="0"/></worksheet>')
                    ]
                },
            )

        with patch.object(engine, "_repack", broken), self.assertRaisesRegex(
            ValueError, "UNAUTHORIZED_XML_BYTES_CHANGED"
        ):
            call(raw, raw)

    def test_corrupted_writer_cannot_modify_opaque_part(self):
        original_repack = engine._repack
        raw = mutate(fixture_bytes(), additions={"opaque/retained.bin": b"unchanged"})

        def broken(candidate, parts):
            return mutate(
                original_repack(candidate, parts),
                {"opaque/retained.bin": [(b"unchanged", b"changed")]},
            )

        with patch.object(engine, "_repack", broken), self.assertRaisesRegex(
            ValueError, "PACKAGE_FOOTPRINT_CHANGED"
        ):
            call(raw, raw)

    def test_original_openpyxl_failure_is_closed_without_cache_fabrication(self):
        source = fixture_bytes()
        source = mutate(
            source,
            {"xl/worksheets/sheet1.xml": [(b"<f>1+1</f>", b'<f aca="1">1+1</f>')]},
        )
        candidate = mutate(
            source,
            {
                "xl/workbook.xml": [
                    (b"Data!$A$1:$B$3", b"'Data'!$A$1:$B$3"),
                    (b'state="hidden"', b'state="visible"'),
                    (b'forceFullCalc="1"', b'forceFullCalc="0"'),
                ],
                "xl/worksheets/sheet1.xml": [
                    (b'<filter val="Open"/>', b'<filter val="Closed"/>')
                ],
            },
            {"opaque/retained.bin": bytes(range(256))},
        )
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "source.xlsx", Path(tmp) / "candidate.xlsx"
            a.write_bytes(source)
            b.write_bytes(candidate)
            old = evaluate_repair(
                a,
                b,
                expected_source_sha=digest(source),
                expected_candidate_sha=digest(candidate),
            )
        self.assertEqual(old["state"], "REJECTED_SERIALIZED_LOSS")
        self.assertTrue(old["content_losses"])
        final, receipt = call(source, candidate)
        self.assertEqual(receipt["remaining_native_losses"], [])
        self.assertEqual(receipt["content_losses"], [])
        self.assertEqual(
            compare_features(snapshot_xlsx(source), snapshot_xlsx(final)), []
        )
        self.assertEqual(
            compare_content(snapshot_xlsx(candidate), snapshot_xlsx(final)), []
        )
        with zipfile.ZipFile(io.BytesIO(final)) as package:
            self.assertEqual(package.read("opaque/retained.bin"), bytes(range(256)))
            self.assertIn(
                b'<f aca="1">1+1</f><v>2</v>', package.read("xl/worksheets/sheet1.xml")
            )
            self.assertIn(
                b">Data!$A$1:$B$3</definedName>", package.read("xl/workbook.xml")
            )
        self.assertEqual(final, call(source, candidate)[0])

    def test_preserves_absent_cache_and_actual_candidate_formula(self):
        source = fixture_bytes()
        candidate = mutate(
            source,
            {
                "xl/worksheets/sheet1.xml": [
                    (b"<f>1+1</f><v>2</v>", b'<f ca="1">2+2</f>')
                ]
            },
        )
        final, receipt = call(source, candidate)
        cell = snapshot_xlsx(final)["cells"]["Data!B3"]
        self.assertEqual(cell["formula"], "2+2")
        self.assertIsNone(cell["value"])
        self.assertEqual(cell["formula_attributes"], {"ca": True})
        self.assertEqual(
            receipt["formula_cache_policy"],
            "PRESERVED_FROM_CANDIDATE_WITHOUT_CALCULATION",
        )

    def test_inserts_missing_features_before_later_schema_children(self):
        source = fixture_bytes()
        with zipfile.ZipFile(io.BytesIO(source)) as package:
            sheet = package.read("xl/worksheets/sheet1.xml")
            start = sheet.index(b"<autoFilter ")
            end = sheet.index(b"</autoFilter>") + len(b"</autoFilter>")
            oldfilter = sheet[start:end]
        candidate = mutate(
            source,
            {
                "xl/worksheets/sheet1.xml": [
                    (
                        oldfilter,
                        b'<mergeCells count="1"><mergeCell ref="C1:D1"/></mergeCells>',
                    )
                ],
                "xl/workbook.xml": [(b'<calcPr forceFullCalc="1"/>', b"")],
            },
        )
        final, _ = call(source, candidate)
        with zipfile.ZipFile(io.BytesIO(final)) as package:
            data = package.read("xl/worksheets/sheet1.xml")
            self.assertLess(data.index(b"<autoFilter"), data.index(b"<mergeCells"))
        self.assertEqual(
            compare_features(snapshot_xlsx(source), snapshot_xlsx(final)), []
        )

    def test_removes_candidate_only_filter_and_names(self):
        candidate = fixture_bytes()
        with zipfile.ZipFile(io.BytesIO(candidate)) as package:
            wb = package.read("xl/workbook.xml")
            sheet = package.read("xl/worksheets/sheet1.xml")
        names = wb[
            wb.index(b"<definedNames>") : wb.index(b"</definedNames>")
            + len(b"</definedNames>")
        ]
        filt = sheet[
            sheet.index(b"<autoFilter ") : sheet.index(b"</autoFilter>")
            + len(b"</autoFilter>")
        ]
        source = mutate(
            candidate,
            {
                "xl/workbook.xml": [(names, b"")],
                "xl/worksheets/sheet1.xml": [(filt, b"")],
            },
        )
        final, _ = call(source, candidate)
        self.assertEqual(
            compare_features(snapshot_xlsx(source), snapshot_xlsx(final)), []
        )

    def test_inherited_source_namespace_is_bound_on_transferred_filter(self):
        raw = fixture_bytes()
        source = mutate(
            raw,
            {
                "xl/worksheets/sheet1.xml": [
                    (
                        b"<worksheet xmlns=",
                        b'<worksheet xmlns:xr="urn:revision" xmlns=',
                    ),
                    (b"<autoFilter ref=", b'<autoFilter xr:uid="abc" ref='),
                ]
            },
        )
        final, _ = call(source, raw)
        self.assertEqual(
            compare_features(snapshot_xlsx(source), snapshot_xlsx(final)), []
        )

    def test_duplicate_scoped_name_still_rejected(self):
        source = fixture_bytes(duplicate_name=True)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SCOPED_DEFINED_NAME"):
            call(source, fixture_bytes())

    def test_wrong_hashes_reject_before_processing(self):
        raw = fixture_bytes()
        for target in ("source", "candidate"):
            with self.subTest(target=target), self.assertRaisesRegex(
                ValueError, target.upper() + "_HASH_MISMATCH"
            ):
                repair_native_package(
                    raw,
                    raw,
                    expected_source_sha="0" * 64 if target == "source" else digest(raw),
                    expected_candidate_sha=(
                        "0" * 64 if target == "candidate" else digest(raw)
                    ),
                )

    def test_hidden_row_difference_not_silently_overridden(self):
        source = fixture_bytes()
        candidate = mutate(
            source,
            {"xl/worksheets/sheet1.xml": [(b'<row r="2" hidden="1">', b'<row r="2">')]},
        )
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_HIDDEN_ROWS_CHANGE"):
            call(source, candidate)

    def test_extension_filter_refused(self):
        raw = fixture_bytes()
        source = mutate(
            raw,
            {
                "xl/worksheets/sheet1.xml": [
                    (b"</autoFilter>", b"<extLst/></autoFilter>")
                ]
            },
        )
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_FILTER_EXTENSION"):
            call(source, raw)

    def test_signature_requires_its_signer(self):
        source = fixture_bytes()
        candidate = mutate(
            source, additions={"_xmlsignatures/sig1.xml": b"<signature/>"}
        )
        with self.assertRaisesRegex(ValueError, "SIGNED_PACKAGE_REQUIRES_SIGNER"):
            call(source, candidate)

    def test_changed_external_link_must_not_receive_source_name(self):
        source = fixture_bytes()
        candidate = mutate(
            source, additions={"xl/externalLinks/externalLink1.xml": b"<externalLink/>"}
        )
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_EXTERNAL_LINK_CHANGE"):
            call(source, candidate)

    def test_text_and_formula_attributes_unchanged_under_prefixes_comments_and_utf8(
        self,
    ):
        raw = fixture_bytes()
        candidate = mutate(
            raw,
            {
                "xl/worksheets/sheet1.xml": [
                    (b"<t>Open</t>", "<t>Étage &amp; 2</t>".encode()),
                    (
                        b"<f>1+1</f>",
                        b'<!-- &gt; --><f t="shared" si="3" ref="B3:B3">1+1</f>',
                    ),
                ]
            },
        )
        final, _ = call(raw, candidate)
        self.assertEqual(
            compare_content(snapshot_xlsx(candidate), snapshot_xlsx(final)), []
        )

    def test_transferred_unquoted_names_and_scopes_remain_exact(self):
        source = fixture_bytes()
        candidate = mutate(
            source, {"xl/workbook.xml": [(b"Data!$A$1:$B$3", b"'Data'!$A$1:$B$3")]}
        )
        final, _ = call(source, candidate)
        self.assertEqual(
            snapshot_xlsx(source)["defined_names"],
            snapshot_xlsx(final)["defined_names"],
        )


if __name__ == "__main__":
    unittest.main()

"""Regression tests for identity, locator safety and review-state separation."""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lane_adapter", ROOT / "tools/qps_binary_bridge_lane_adapter.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot import lane adapter under test")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)
UPSTREAM = Path(
    os.environ.get(
        "QPS_BRIDGE_UPSTREAM_PATH", str(ROOT / "tools/qps_binary_bridge.py")
    )
)


def context(
    member: str = "origin/source.html",
    receipt: str = "arrival-A",
    index: int = 0,
) -> dict[str, Any]:
    """Create a synthetic archive occurrence with a caller-controlled identity."""
    return {
        "receipt_id": receipt,
        "container_chain": [
            {"sha256": "a" * 64, "member_path": "batch.zip", "member_index": 0}
        ],
        "member_path": member,
        "member_index": index,
    }


def six_page_pdf() -> bytes:
    """Build a valid uncompressed PDF with a sentinel only on its sixth page."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 6 /Kids [3 0 R 5 0 R 7 0 R 9 0 R 11 0 R 13 0 R] >>",
    ]
    for page_index in range(6):
        text = b"ONLY_PAGE_SIX" if page_index == 5 else b"ordinary"
        stream = b"BT /F1 12 Tf 20 20 Td (" + text + b") Tj ET"
        page = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            "/Resources << /Font << /F1 15 0 R >> >> "
            f"/Contents {4 + 2 * page_index} 0 R >>"
        ).encode()
        content = (
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
        objects.extend([page, content])
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    data = b"%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    trailer = (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    )
    return data + trailer.encode()


class LaneAdapterTests(unittest.TestCase):
    """Exercise the opt-in envelope using synthetic sources only."""

    def setUp(self) -> None:
        """Create isolated source storage for each test."""
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        """Remove the isolated test files."""
        self.temp.cleanup()

    def source(self, path: str, text: str = "same bytes") -> Path:
        """Write a small HTML source at the requested fixture path."""
        source_path = self.root / path
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(f"<html><p>{text}</p></html>")
        return source_path

    def normalize(
        self,
        path: Path,
        ctx: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Normalize a fixture through the exact pinned upstream bridge."""
        return adapter.normalize_lane_source(
            path,
            ctx or context(),
            source_authority="OWNER_ASSERTED",
            upstream_path=UPSTREAM,
            **kwargs,
        )

    def test_same_basename_different_bytes_cannot_collide(self) -> None:
        a = self.normalize(
            self.source("a/source.html", "alpha"), context("a/source.html")
        )
        b = self.normalize(
            self.source("b/source.html", "beta"), context("b/source.html")
        )
        self.assertEqual(a["legacy_source_id"], b["legacy_source_id"])
        self.assertNotEqual(a["content_id"], b["content_id"])
        self.assertNotEqual(a["source_id"], b["source_id"])

    def test_same_bytes_different_paths_deduplicate_content_only(self) -> None:
        a = self.normalize(self.source("a/source.html"), context("a/source.html"))
        b = self.normalize(self.source("b/source.html"), context("b/source.html"))
        self.assertEqual(a["content_id"], b["content_id"])
        self.assertNotEqual(a["occurrence_id"], b["occurrence_id"])

    def test_repeated_arrival_and_duplicate_zip_entry_survive(self) -> None:
        path = self.source("source.html")
        a = self.normalize(path, context(receipt="A", index=0))
        b = self.normalize(path, context(receipt="B", index=0))
        c = self.normalize(path, context(receipt="A", index=1))
        self.assertEqual(len({item["content_id"] for item in [a, b, c]}), 1)
        self.assertEqual(len({item["occurrence_id"] for item in [a, b, c]}), 3)

    def test_changed_outer_archive_changes_occurrence_not_content(self) -> None:
        path = self.source("source.html")
        ctx = context()
        changed = copy.deepcopy(ctx)
        changed["container_chain"][0]["sha256"] = "b" * 64
        a = self.normalize(path, ctx)
        b = self.normalize(path, changed)
        self.assertEqual(a["content_id"], b["content_id"])
        self.assertNotEqual(a["occurrence_id"], b["occurrence_id"])

    def test_invalid_or_missing_context_fails(self) -> None:
        with self.assertRaises(ValueError):
            adapter.validate_context({"member_path": "a"})
        bad = context()
        bad["member_index"] = True
        with self.assertRaises(ValueError):
            adapter.validate_context(bad)
        bad = context()
        bad["container_chain"][0]["sha256"] = "not-a-hash"
        with self.assertRaises(ValueError):
            adapter.validate_context(bad)

    def test_pin_mismatch_is_rejected_before_import(self) -> None:
        path = self.root / "changed.py"
        path.write_bytes(
            UPSTREAM.read_bytes() + b"\nraise RuntimeError('must never execute')\n"
        )
        with self.assertRaisesRegex(ValueError, "pin mismatch"):
            adapter.load_pinned_bridge(path)

    def test_pinned_loader_does_not_reopen_source_or_bytecode(self) -> None:
        """Load the checked snapshot even if its path later changes."""
        path = self.root / "upstream_copy.py"
        original = UPSTREAM.read_bytes()
        path.write_bytes(original)
        loader_class = adapter._PinnedBytesLoader
        real_exec = loader_class.exec_module

        def replace_path_before_import(loader, module):
            path.write_bytes(b"raise RuntimeError('unverified source executed')\n")
            return real_exec(loader, module)

        with patch.object(loader_class, "exec_module", replace_path_before_import):
            with patch.object(
                loader_class,
                "get_data",
                side_effect=AssertionError("source or pycache re-read"),
            ):
                bridge = adapter.load_pinned_bridge(path)
        self.assertTrue(callable(bridge.normalize_source))
        self.assertNotEqual(path.read_bytes(), original)

    def test_pdf_literal_fallback_never_mints_page_one(self) -> None:
        path = self.root / "six.pdf"
        path.write_bytes(six_page_pdf())
        with patch.dict(sys.modules, {"pypdf": None}):
            result = self.normalize(path, context("six.pdf"), requested_depth="deep")
        node = result["hierarchy_node"]
        self.assertEqual(node["pages"], [])
        self.assertIn("ONLY_PAGE_SIX", node["unlocated_fragments"][0]["text"])
        self.assertNotIn('"page:1"', json.dumps(result))
        self.assertEqual(node["unverified_page_marker_estimate"], 6)
        self.assertFalse(result["citation_policy"]["page_citations_allowed"])
        self.assertEqual(result["coverage"]["stage"], "SCOUT")
        self.assertTrue(result["coverage"]["deep_read_pending"])
        self.assertFalse(result["coverage"]["deep_read_complete"])
        self.assertNotEqual(
            result["semantic_sha256"], result["upstream_semantic_sha256"]
        )

    def test_structured_pdf_keeps_real_page_anchors_without_acceptance(self) -> None:
        fake = types.ModuleType("pypdf")

        class Page:
            """Return text as a structured page-parser fixture."""

            def __init__(self, text: str) -> None:
                self.text = text

            def extract_text(self) -> str:
                """Return this page's fixture text."""
                return self.text

        class Reader:
            """Expose two ordered pages for the structured parser path."""

            def __init__(self, path: Path) -> None:
                self.pages = [Page("first"), Page("second")]

        fake.PdfReader = Reader
        path = self.root / "structured.pdf"
        path.write_bytes(six_page_pdf())
        with patch.dict(sys.modules, {"pypdf": fake}):
            result = self.normalize(path, context("structured.pdf"))
        anchors = [page["anchor"] for page in result["hierarchy_node"]["pages"]]
        self.assertEqual(anchors, ["page:1", "page:2"])
        self.assertTrue(result["citation_policy"]["page_citations_allowed"])
        self.assertEqual(result["authority_state"], "DERIVED_UNREVIEWED")
        self.assertFalse(result["ssot_promotion_allowed"])

    def test_requested_deep_and_source_current_do_not_promote(self) -> None:
        result = self.normalize(
            self.source("source.html"),
            requested_depth="deep",
            source_lifecycle="APPROVED",
        )
        self.assertEqual(result["source_lifecycle_claim"], "APPROVED")
        self.assertEqual(result["authority_state"], "DERIVED_UNREVIEWED")
        self.assertEqual(result["owner_disposition"], "PENDING")
        self.assertEqual(result["coverage"]["completeness"], "PARTIAL")
        self.assertFalse(result["ssot_promotion_allowed"])

    def test_adapter_preserves_input_and_downgrades_lineage_claim(self) -> None:
        bridge = adapter.load_pinned_bridge(UPSTREAM)
        path = self.source("source.html")
        raw = bridge.normalize_source(
            path,
            authority="OWNER",
            lifecycle_status="CURRENT",
            trace_links=[],
            supersedes=["older-basename.xlsx"],
            producer_commit=adapter.UPSTREAM_REF,
        )
        before = copy.deepcopy(raw)
        out = adapter.adapt_source(raw, context())
        self.assertEqual(raw, before)
        self.assertEqual(
            out["lineage_candidates"][0]["state"], "CALLER_CLAIM_UNVERIFIED"
        )
        self.assertNotIn("supersedes", out)

    def test_stale_semantic_hash_is_rejected(self) -> None:
        bridge = adapter.load_pinned_bridge(UPSTREAM)
        path = self.source("source.html")
        raw = bridge.normalize_source(
            path,
            authority="OWNER",
            lifecycle_status="CURRENT",
            trace_links=[],
            supersedes=[],
            producer_commit=adapter.UPSTREAM_REF,
        )
        raw["hierarchy_node"]["blocks"][0]["text"] = "changed"
        with self.assertRaisesRegex(ValueError, "semantic hash"):
            adapter.adapt_source(raw, context())

    def test_deterministic_identity_and_byte_hashes(self) -> None:
        path = self.source("source.html")
        a = self.normalize(path)
        b = self.normalize(path)
        self.assertEqual(a, b)
        self.assertEqual(
            a["artifact_hashes"]["semantic_sha256"],
            adapter.canonical_hash(a["hierarchy_node"]),
        )

    def test_cli_rejects_output_aliases_without_changing_inputs(self) -> None:
        source = self.source("source.html")
        context_path = self.root / "context.json"
        context_path.write_text(json.dumps(context()))
        upstream = self.root / "bridge.py"
        upstream.write_bytes(UPSTREAM.read_bytes())
        protected = {
            "source": source,
            "context": context_path,
            "upstream": upstream,
        }
        original_bytes = {path: path.read_bytes() for path in protected.values()}
        outputs = []
        for label, path in protected.items():
            outputs.append((label, "direct", path))
            symlink = self.root / f"{label}-symlink"
            symlink.symlink_to(path)
            outputs.append((label, "symlink", symlink))
            hardlink = self.root / f"{label}-hardlink"
            os.link(path, hardlink)
            outputs.append((label, "hardlink", hardlink))
        for label, alias_kind, output in outputs:
            arguments = [
                "qps_binary_bridge_lane_adapter.py",
                str(source),
                "--occurrence-context", str(context_path),
                "--source-authority", "OWNER_ASSERTED",
                "--upstream-path", str(upstream),
                "--output", str(output),
            ]
            with self.subTest(input=label, alias=alias_kind):
                with patch.object(sys, "argv", arguments):
                    with patch.object(sys, "stderr", io.StringIO()) as stderr:
                        with patch.object(adapter, "normalize_lane_source") as normalize:
                            with self.assertRaises(SystemExit) as rejected:
                                adapter.main()
                self.assertEqual(rejected.exception.code, 2)
                self.assertIn("output must not overwrite", stderr.getvalue())
                normalize.assert_not_called()
                for path, before in original_bytes.items():
                    self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

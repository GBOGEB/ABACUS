#!/usr/bin/env python3
"""Opt-in lane envelope for the pinned ABACUS v1 binary bridge.

This proposal leaves v1 producers/consumers unchanged. It separates content from
arrival identity, removes invented PDF page locations, and makes extraction
coverage and review authority independent. Inputs must pass archive admission
before this adapter; it is not a ZIP intake engine or a deep-reading engine.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import re
from pathlib import Path
from types import CodeType, ModuleType
from typing import Any

SCHEMA = "abacus-binary-bridge-lane/v1"
VERSION = "0.1.0-proposal"
UPSTREAM_REPOSITORY = "GBOGEB/ABACUS"
UPSTREAM_REF = "ecc601294ffdc5e1ba167071581921bf09939d00"
UPSTREAM_SOURCE_SHA256 = "daf90d0df06e18caaa4262bf99543cd986def26245c88f3e461a18111c6ebafd"
UPSTREAM_GIT_BLOB_SHA1 = "31b8f1826251949f18350f9c86856b6b7b1be6ba"
UPSTREAM_PATH = Path(__file__).with_name("qps_binary_bridge.py")
MAX_SOURCE_BYTES = 256 * 1024 * 1024


def canonical_hash(value: object) -> str:
    """Hash a stable UTF-8 JSON representation."""
    data = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def checked_hash(value: Any, field: str) -> str:
    """Require an explicit lowercase byte digest."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def validate_context(context: dict[str, Any]) -> dict[str, Any]:
    """Preserve exact original member spelling and duplicate-entry index."""
    required = {"receipt_id", "container_chain", "member_path", "member_index"}
    if not isinstance(context, dict) or set(context) != required:
        fields = ", ".join(sorted(required))
        raise ValueError("occurrence context must contain exactly " + fields)
    for key in ("receipt_id", "member_path"):
        if not isinstance(context[key], str) or not context[key].strip():
            raise ValueError(f"{key} must be nonempty")
    if type(context["member_index"]) is not int or context["member_index"] < 0:
        raise ValueError("member_index must be a nonnegative ZIP directory index")
    if not isinstance(context["container_chain"], list):
        raise ValueError("container_chain must be ordered outermost to innermost")
    for container in context["container_chain"]:
        fields = {"sha256", "member_path", "member_index"}
        if not isinstance(container, dict) or set(container) != fields:
            raise ValueError(
                "each container needs sha256, member_path and member_index"
            )
        checked_hash(container["sha256"], "container sha256")
        member_path = container["member_path"]
        if not isinstance(member_path, str) or not member_path.strip():
            raise ValueError("container member_path must be nonempty")
        member_index = container["member_index"]
        if type(member_index) is not int or member_index < 0:
            raise ValueError("container member_index must be nonnegative")
    return copy.deepcopy(context)


class _PinnedBytesLoader(importlib.machinery.SourceFileLoader):
    """Import only the checked bytes; never reread a mutable source or pycache."""

    def __init__(self, fullname: str, path: Path, verified_bytes: bytes) -> None:
        super().__init__(fullname, str(path))
        self._verified_bytes = verified_bytes

    def get_code(self, fullname: str) -> CodeType:
        """Compile the verified in-memory bytes instead of a path lookup."""
        if fullname != self.name:
            raise ImportError("pinned bridge loader module identity mismatch")
        return self.source_to_code(self._verified_bytes, self.path)


def load_pinned_bridge(path: Path = UPSTREAM_PATH) -> ModuleType:
    """Verify exact upstream bytes and execute only that immutable snapshot."""
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != UPSTREAM_SOURCE_SHA256:
        raise ValueError(
            "upstream source pin mismatch; review and repin before importing"
        )
    module_name = "qps_binary_bridge_pinned_lane"
    loader = _PinnedBytesLoader(module_name, path, raw)
    spec = importlib.util.spec_from_loader(module_name, loader, origin=str(path))
    if spec is None:
        raise RuntimeError("cannot import pinned upstream bridge")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


SCOPES = {
    "docx": {
        "covered": ["main-body paragraph text", "main-body table text"],
        "uncovered": [
            "comments",
            "revision attribution/deletions",
            "headers/footers",
            "notes",
            "drawings",
        ],
    },
    "xlsx": {
        "covered": ["stored worksheet values", "formula text/shared attributes"],
        "uncovered": [
            "native recalculation",
            "comments",
            "styles",
            "sheet visibility metadata",
            "drawings/charts",
            "external resolution",
        ],
    },
    "pptx": {
        "covered": ["slide-part text"],
        "uncovered": [
            "presentation relationship order",
            "notes",
            "geometry",
            "rendering",
        ],
    },
    "pdf": {
        "covered": ["pypdf page text"],
        "uncovered": [
            "OCR",
            "layout/reading-order validation",
            "visual validation",
        ],
    },
    "html": {
        "covered": ["static HTML text blocks"],
        "uncovered": ["dynamic content", "external assets", "visual validation"],
    },
}


def adapt_source(
    record: dict[str, Any],
    context: dict[str, Any],
    *,
    requested_depth: str = "structural",
) -> dict[str, Any]:
    """Produce an opt-in envelope without inferring acceptance from parsing."""
    if requested_depth not in {"scout", "structural", "deep"}:
        raise ValueError("requested_depth must be scout, structural or deep")
    context = validate_context(context)
    byte_hash = checked_hash(record.get("source_sha256"), "source_sha256")
    original = record["hierarchy_node"]
    if canonical_hash(original) != record.get("semantic_sha256"):
        raise ValueError("upstream semantic hash does not match hierarchy")
    producer_matches = (
        record.get("producer_commit") == UPSTREAM_REF
        and record.get("producer_repository") == UPSTREAM_REPOSITORY
    )
    if not producer_matches:
        raise ValueError("upstream producer reference mismatch")
    hierarchy = copy.deepcopy(original)
    kind = hierarchy.get("kind")
    quality = copy.deepcopy(hierarchy.get("extraction_quality", {}))
    is_fallback = quality.get("status") == "FALLBACK"
    scope = copy.deepcopy(
        SCOPES.get(kind, {"covered": [], "uncovered": ["unknown parser scope"]})
    )
    page_citations_allowed = (
        kind == "pdf"
        and not is_fallback
        and quality.get("parser") == "pypdf"
    )
    if kind == "pdf" and is_fallback:
        # V1 aggregates unassigned literals into page:1. Preserve text without
        # any page locator, and retain the old semantic hash only as provenance.
        text = "\n".join(
            page.get("text", "")
            for page in hierarchy.get("pages", [])
            if page.get("text")
        )
        marker_estimate = len(hierarchy.get("pages", []))
        fragments = []
        if text:
            fragments.append(
                {
                    "anchor": "document:unlocated:1",
                    "text": text,
                    "locator_scope": "document_unlocated",
                }
            )
        hierarchy = {
            "kind": "pdf",
            "pages": [],
            "unlocated_fragments": fragments,
            "unverified_page_marker_estimate": marker_estimate,
            "extraction_quality": {
                **quality,
                "locator_state": "UNLOCATED",
                "page_citations_allowed": False,
            },
        }
        scope = {
            "covered": ["unlocated uncompressed literal-string scout"],
            "uncovered": [
                "page attribution",
                "page completeness",
                "reading order",
                "compressed text",
                "OCR",
                "layout",
            ],
        }
    stage = "SCOUT" if is_fallback else "STRUCTURAL"
    semantic_hash = canonical_hash(hierarchy)
    occurrence_hash = canonical_hash(
        {"context": context, "source_sha256": byte_hash}
    )
    producer = {
        "repository": UPSTREAM_REPOSITORY,
        "ref": UPSTREAM_REF,
        "path": "tools/qps_binary_bridge.py",
        "source_sha256": UPSTREAM_SOURCE_SHA256,
        "git_blob_sha1": UPSTREAM_GIT_BLOB_SHA1,
    }
    return {
        "schema": SCHEMA,
        "source_id": "occurrence:sha256:" + occurrence_hash,
        "occurrence_id": "occurrence:sha256:" + occurrence_hash,
        "content_id": "sha256:" + byte_hash,
        "source_sha256": byte_hash,
        "legacy_source_id": record.get("source_id"),
        "staged_source_path": record.get("source_path"),
        "occurrence_context": context,
        "hierarchy_node": hierarchy,
        "semantic_sha256": semantic_hash,
        "upstream_semantic_sha256": record["semantic_sha256"],
        "coverage": {
            "requested_depth": requested_depth,
            "stage": stage,
            "completeness": "PARTIAL",
            "deep_read_complete": False,
            "deep_read_pending": requested_depth == "deep",
            **scope,
        },
        "citation_policy": {
            "page_citations_allowed": page_citations_allowed,
            "logical_slide_citations_allowed": False,
            "source_bound_structural_anchors_only": not is_fallback,
            "reason": (
                "Fallback literals have no page attribution; PPTX numeric part "
                "order is not validated logical deck order."
            ),
        },
        "authority_state": "DERIVED_UNREVIEWED",
        "source_authority_claim": record.get("authority"),
        "source_lifecycle_claim": record.get("lifecycle_status"),
        "owner_disposition": "PENDING",
        "ssot_promotion_allowed": False,
        "freshness_state": "PARSED_BYTES_SNAPSHOT",
        "lineage_candidates": [
            {
                "relationship": "supersedes",
                "target": target,
                "state": "CALLER_CLAIM_UNVERIFIED",
            }
            for target in record.get("supersedes", [])
        ],
        "trace_links": copy.deepcopy(record.get("trace_links", [])),
        "producer_chain": {
            "upstream": producer,
            "adapter": {
                "version": VERSION,
                "state": "LOCAL_PROPOSAL",
                "source_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
            },
        },
        "artifact_hashes": {
            "source_sha256": byte_hash,
            "semantic_sha256": semantic_hash,
            "upstream_semantic_sha256": record["semantic_sha256"],
        },
    }


def normalize_lane_source(
    path: Path,
    context: dict[str, Any],
    *,
    source_authority: str,
    source_lifecycle: str = "UNKNOWN",
    requested_depth: str = "structural",
    upstream_path: Path = UPSTREAM_PATH,
) -> dict[str, Any]:
    """Run the pinned producer on admitted bytes and wrap its result."""
    validate_context(context)
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("source exceeds lane-adapter admission byte limit")
    bridge = load_pinned_bridge(upstream_path)
    record = bridge.normalize_source(
        path,
        authority=source_authority,
        lifecycle_status=source_lifecycle,
        trace_links=[],
        supersedes=[],
        producer_commit=UPSTREAM_REF,
    )
    return adapt_source(record, context, requested_depth=requested_depth)


def main() -> int:
    """Write one opt-in envelope from an explicit occurrence-context JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--occurrence-context", type=Path, required=True)
    parser.add_argument("--source-authority", required=True)
    parser.add_argument("--source-lifecycle", default="UNKNOWN")
    parser.add_argument(
        "--requested-depth",
        choices=["scout", "structural", "deep"],
        default="structural",
    )
    parser.add_argument("--upstream-path", type=Path, default=UPSTREAM_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output_path = args.output.resolve()
    protected_paths = {
        "source": args.source,
        "occurrence context": args.occurrence_context,
        "upstream bridge": args.upstream_path,
    }
    for label, input_path in protected_paths.items():
        same_resolved_path = output_path == input_path.resolve()
        same_existing_file = (
            args.output.exists()
            and input_path.exists()
            and args.output.samefile(input_path)
        )
        if same_resolved_path or same_existing_file:
            parser.error(f"output must not overwrite the {label} or an alias")
    result = normalize_lane_source(
        args.source,
        json.loads(args.occurrence_context.read_text()),
        source_authority=args.source_authority,
        source_lifecycle=args.source_lifecycle,
        requested_depth=args.requested_depth,
        upstream_path=args.upstream_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

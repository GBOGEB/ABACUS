"""Contract tests for the GitHub Pages bundle published by deploy-docs.yml.

These replace the old `validate` job of deploy-docs.yml (required pages exist,
every docs HTML file is closed, internal links resolve) and run inside the hub
reusable CI before the bundle is built. They read the source tree under docs/
and the build inputs, and exercise tools/gate_rollup.py (stdlib only), so they
need nothing beyond pytest.
"""

import importlib.util
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

ENTRY_TITLE = "<title>ABACUS – Recursive Multi-Agent Cryogenic Analysis System</title>"

# The same four pages the old validate job required.
REQUIRED_HTML = [
    "index.html",
    "handover_book.html",
    "deep_analysis_dashboard.html",
    "dashboard.html",
]

# Files the build-command in deploy-docs.yml reads.
BUILD_INPUTS = [
    "build_qplant_visualization.py",
    "content/qplant/process_flow.yaml",
    "content/qplant/thermodynamics.yaml",
    "content/qplant/lifecycle.yaml",
    "content/qplant/utilities.yaml",
    "tools/gate_rollup.py",
    "rtm/trace_matrix.json",
    "scripts/validate_runtime_foundation.py",
    "scripts/write_runtime_governance_status.py",
]

HREF = re.compile(rb'href="([^"]+)"')
# The deploy readback builds URLs as base + path without quoting.
URL_UNSAFE = re.compile(r"[ #?%]")


def _docs_html():
    return sorted(p for p in DOCS.rglob("*.html") if p.is_file())


def test_entry_page_keeps_its_title():
    index = DOCS / "index.html"
    assert index.is_file()
    assert ENTRY_TITLE in index.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", REQUIRED_HTML)
def test_required_html_page_exists(name):
    assert (DOCS / name).is_file(), f"missing docs/{name}"


def test_every_docs_html_file_is_closed():
    pages = _docs_html()
    assert pages, "no HTML files under docs/"
    unclosed = [p.relative_to(ROOT).as_posix() for p in pages if b"</html>" not in p.read_bytes()]
    assert unclosed == []


def test_internal_links_into_the_bundle_resolve():
    """Port of the old link check (same href filter, same path rule).

    The old job only warned. Here a relative link that lands inside docs/
    (that is, inside the published bundle) and has no target fails. Links
    that leave docs/ point at repository files that Pages never serves; they
    are reported as warnings, as before. hrefs built by JavaScript string
    concatenation (they contain a quote, '+' or '${') are not links.
    """
    broken, outside = [], []
    docs_root = os.path.normpath(str(DOCS))
    for page in _docs_html():
        for raw in HREF.findall(page.read_bytes()):
            href = raw.decode("utf-8", "replace")
            if href.startswith(("http", "#", "mailto")):
                continue
            if any(tok in href for tok in ("'", '"', "+", "${")):
                continue
            target = f"{page.parent.as_posix()}/{href}".split("#", 1)[0].split("?", 1)[0]
            if os.path.exists(target):
                continue
            where = (page.relative_to(ROOT).as_posix(), href)
            resolved = os.path.normpath(target)
            if resolved == docs_root or resolved.startswith(docs_root + os.sep):
                broken.append(where)
            else:
                outside.append(where)
    for page, href in outside:
        print(f"warning: link leaves the Pages bundle: {page} -> {href}")
    assert broken == []


def test_bundle_file_names_need_no_url_quoting():
    unsafe = [
        p.relative_to(DOCS).as_posix()
        for p in DOCS.rglob("*")
        if p.is_file() and URL_UNSAFE.search(p.relative_to(DOCS).as_posix())
    ]
    assert unsafe == []


@pytest.mark.parametrize("rel", BUILD_INPUTS)
def test_build_input_exists(rel):
    assert (ROOT / rel).is_file(), f"build input missing: {rel}"


def _load_gate_rollup():
    spec = importlib.util.spec_from_file_location("gate_rollup", ROOT / "tools" / "gate_rollup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_rollup_writes_the_dashboard_feed(tmp_path):
    """The build runs tools/gate_rollup.py to write docs/dashboard-gates.json."""
    gate_rollup = _load_gate_rollup()
    log = tmp_path / "ci-runs.jsonl"
    rows = [
        {"pr_id": "12", "gate_name": "lint", "exit_code": 1, "timestamp": "2026-10-30T12:00:00Z"},
        {"pr_id": "12", "gate_name": "tests", "exit_code": 0, "timestamp": "2026-10-30T12:05:00Z"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n", encoding="utf-8")
    out = gate_rollup.write_gate_rollup(output_path=tmp_path / "dashboard-gates.json", log_path=log)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["source"]["records_read"] == 3
    assert payload["source"]["malformed_lines"] == 1
    [row] = payload["prs"]
    assert row["pr_id"] == "12" and row["status"] == "FAIL"
    assert row["first_failed_gate"] == "lint" and row["total_gates_run"] == 2
    empty = gate_rollup.build_gate_rollup(tmp_path / "absent.jsonl")
    assert empty["prs"] == [] and empty["source"]["records_read"] == 0

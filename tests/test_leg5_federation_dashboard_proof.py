from __future__ import annotations

import json
from pathlib import Path

from build_federation_dashboard import (
    FEDERATION_REPOS,
    _extract_federation_status,
    build_federation_dashboard,
)


def _write_inputs(root: Path) -> dict[str, Path]:
    metrics = root / "metrics" / "federation"
    metrics.mkdir(parents=True)

    rollup = metrics / "federation_rollup.json"
    rollup.write_text(
        json.dumps(
            {
                "forward_pca": "100%",
                "backward_pca": "100%",
                "geti": "0.97",
                "pci": "0.96",
                "expansion_factor": "1.2",
                "federation_status": {
                    "CODEX": "active",
                    "QPLANT": "active",
                    "ARTSTYLE": "active",
                    "ABACUS": "active",
                    "NONCANONICAL": "must-not-render",
                },
                "wave_progress": {"W000": "done"},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    scree = metrics / "federation_scree.json"
    scree.write_text(json.dumps({"components": []}, sort_keys=True), encoding="utf-8")

    runtime_registry = metrics / "runtime_registry.json"
    runtime_registry.write_text(
        json.dumps(
            {
                "repositories": {
                    "CODEX": {"runtime_evidence": "verified"},
                    "QPLANT": {"runtime_evidence": "verified"},
                    "ARTSTYLE": {"runtime_evidence": "verified"},
                    "ABACUS": {"runtime_evidence": "verified"},
                    "NONCANONICAL": {"runtime_evidence": "must-not-render"},
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    runtime_report = root / "reports" / "runtime_registry_report.json"
    runtime_report.parent.mkdir(parents=True, exist_ok=True)
    runtime_report.write_text(
        json.dumps(
            {
                "repositories": {
                    "CODEX": {"runtime_coverage": "96%"},
                    "QPLANT": {"runtime_coverage": "94%"},
                    "ARTSTYLE": {"runtime_coverage": "93%"},
                    "ABACUS": {"runtime_coverage": "95%"},
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    bottleneck = root / "bottleneck_report.json"
    bottleneck.write_text(json.dumps({}, sort_keys=True), encoding="utf-8")

    return {
        "rollup": rollup,
        "scree": scree,
        "runtime_registry": runtime_registry,
        "runtime_report": runtime_report,
        "bottleneck": bottleneck,
    }


def test_federation_status_uses_canonical_member_order_and_filters_unknown() -> None:
    payload = {
        "federation_status": {
            "CODEX": "active",
            "QPLANT": "active",
            "ARTSTYLE": "active",
            "ABACUS": "active",
            "NONCANONICAL": "must-not-render",
        }
    }

    status = _extract_federation_status(payload)

    assert tuple(status) == FEDERATION_REPOS
    assert "NONCANONICAL" not in status


def test_federation_dashboard_build_is_byte_deterministic(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    first_html = tmp_path / "out-a" / "dashboard.html"
    first_status = tmp_path / "out-a" / "dashboard_status.json"
    second_html = tmp_path / "out-b" / "dashboard.html"
    second_status = tmp_path / "out-b" / "dashboard_status.json"

    common = {
        "rollup_path": paths["rollup"],
        "scree_path": paths["scree"],
        "runtime_registry_path": paths["runtime_registry"],
        "runtime_registry_report_path": paths["runtime_report"],
        "bottleneck_path": paths["bottleneck"],
    }

    build_federation_dashboard(
        **common,
        output_path=first_html,
        status_output_path=first_status,
    )
    build_federation_dashboard(
        **common,
        output_path=second_html,
        status_output_path=second_status,
    )

    assert first_html.read_bytes() == second_html.read_bytes()
    assert first_status.read_bytes() == second_status.read_bytes()

    html = first_html.read_text(encoding="utf-8")
    canonical_positions = [html.index(repo) for repo in FEDERATION_REPOS]
    assert canonical_positions == sorted(canonical_positions)
    assert "NONCANONICAL" not in html


def test_status_receipt_is_time_independent_and_bounded(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    output = tmp_path / "docs" / "dashboard.html"
    status_path = tmp_path / "reports" / "dashboard_status.json"

    build_federation_dashboard(
        rollup_path=paths["rollup"],
        scree_path=paths["scree"],
        runtime_registry_path=paths["runtime_registry"],
        runtime_registry_report_path=paths["runtime_report"],
        bottleneck_path=paths["bottleneck"],
        output_path=output,
        status_output_path=status_path,
    )

    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert "generated_at" not in status
    assert status == {
        "wave": "W005.2",
        "status": "dashboard_generated",
        "dashboard_generated": True,
        "github_pages_compatible": True,
        "json_consumed": True,
        "runtime_registry_consumed": True,
    }

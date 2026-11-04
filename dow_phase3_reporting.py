"""Fail-closed DOW Phase 3 renderer of digest-checked candidate data."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from dow_phase2_statistics import METHOD, SCHEMA, SEMANTICS, digest


def report(metadata_path: Path, destination: Path) -> tuple[Path, Path]:
    """Validate the producer metadata digest before generating real reports."""
    raw = metadata_path.read_bytes()
    if not raw or len(raw) > 5_000_000:
        raise ValueError("missing or oversized metadata")
    metadata = json.loads(raw.decode("utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("Phase 2 metadata is not an object")
    payload = dict(metadata)
    signature = payload.pop("receipt_sha256", None)
    if (
        not isinstance(signature, str)
        or len(signature) != 64
        or digest(payload) != signature
    ):
        raise ValueError("Phase 2 receipt digest mismatch")
    if (
        payload.get("schema"),
        payload.get("method"),
        payload.get("semantics_status"),
    ) != (SCHEMA, METHOD, SEMANTICS):
        raise ValueError("unrecognized Phase 2 statistical method")
    groups, comparisons = payload.get("groups"), payload.get("comparisons")
    if (
        not isinstance(groups, dict)
        or len(groups) < 2
        or not isinstance(comparisons, list)
        or not comparisons
    ):
        raise ValueError("Phase 2 metadata lacks validated groups or comparisons")
    if (
        not math.isfinite(payload.get("alpha", float("nan")))
        or not 0 < payload["alpha"] < 1
    ):
        raise ValueError("invalid alpha")
    for name, row in groups.items():
        if (
            not isinstance(name, str)
            or not isinstance(row, dict)
            or row.get("n", 0) < 2
        ):
            raise ValueError("invalid group row")
        values = [
            row.get("mean"),
            row.get("sample_std"),
            *(row.get("bootstrap_ci") or []),
        ]
        if len(values) != 4 or not all(
            isinstance(v, (float, int)) and math.isfinite(v) for v in values
        ):
            raise ValueError("invalid group statistics")
    output = {
        "schema": "abacus.dow.phase3.bootstrap.candidate.v1",
        "metadata_receipt_sha256": signature,
        "source_sha256": payload["source_sha256"],
        "method": METHOD,
        "semantics_status": SEMANTICS,
        "alpha": payload["alpha"],
        "groups": groups,
        "comparisons": comparisons,
        "interpretation": "Descriptive percentile bootstrap intervals only; no formal hypothesis decision.",
        "merge_admission": "HOLD",
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }
    out = destination / f"report-{signature[:12]}"
    json_path = out.with_suffix(".json")
    markdown_path = out.with_suffix(".md")
    lines = [
        "# DOW Phase 3 — candidate bootstrap report",
        "",
        "Status: **PROVISIONAL_REVIEW_REQUIRED**. No engineering or admission authority.",
        "",
        f"Source SHA-256: `{output['source_sha256']}`",
        "",
        f"Phase 2 receipt: `{signature}`",
        "",
        f"Bootstrap alpha: {output['alpha']}",
        "",
        "## Groups",
        "",
    ]
    for name, item in sorted(groups.items()):
        safe_name = name.replace("\n", " ").replace("|", "\\|").replace("`", "'")
        lines.append(
            f"- {safe_name}: n={item['n']}, mean={item['mean']:.5g}, "
            f"bootstrap interval=[{item['bootstrap_ci'][0]:.5g}, {item['bootstrap_ci'][1]:.5g}]"
        )
    lines.extend(["", "## Pairwise differences", ""])
    for row in comparisons:
        lines.append(
            f"- Difference (right minus left): {row['estimate_right_minus_left']:.5g}; "
            f"interval=[{row['bootstrap_ci'][0]:.5g}, {row['bootstrap_ci'][1]:.5g}]"
        )
    lines.extend(
        [
            "",
            "Descriptive intervals are not a formal acceptance or rejection decision.",
            "",
        ]
    )
    destination.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase2-metadata", type=Path, required=True)
    parser.add_argument("--reports-root", type=Path, default=Path("phase3_reports"))
    args = parser.parse_args(argv)
    try:
        paths = report(args.phase2_metadata, args.reports_root)
    except (
        OSError,
        ValueError,
        UnicodeError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        parser.exit(2, f"Phase 3 input contract failed: {exc}\n")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

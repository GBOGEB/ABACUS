"""Deterministic candidate DOW Phase 2 bootstrap statistics producer.

Statistical semantics are provisional and confer no engineering/admission credit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from itertools import combinations
from pathlib import Path
from statistics import mean, stdev

from bootstrap_eval import bootstrap_ci_diff_means, bootstrap_ci_mean

SCHEMA = "abacus.dow.phase2.bootstrap.candidate.v1"
METHOD = "percentile-bootstrap-mean-and-ordered-difference"
SEMANTICS = "PROVISIONAL_REVIEW_REQUIRED"
BOOTSTRAPS = 2000
SEED = 20261014


def digest(payload: dict) -> str:
    """Digest a canonical, NaN-free JSON dictionary."""
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def measure(source: Path, destination: Path, alpha: float = 0.05) -> Path:
    """Read strict group/score CSV, compute seeded CIs, and write metadata."""
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be finite and strictly between 0 and 1")
    raw = source.read_bytes()
    if not raw or len(raw) > 10_000_000:
        raise ValueError("CSV must be nonempty and at most 10 MB")
    data_sha = hashlib.sha256(raw).hexdigest()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not reader.fieldnames or not {"group", "score"}.issubset(reader.fieldnames):
        raise ValueError("CSV must contain group and score columns")
    groups: dict[str, list[float]] = {}
    for row in reader:
        if None in row or row["group"] is None or row["score"] is None:
            raise ValueError("CSV row is malformed")
        group = row["group"].strip()
        if not group or len(group) > 128:
            raise ValueError("group label is missing or too long")
        try:
            value = float(row["score"])
        except ValueError as exc:
            raise ValueError("score is not numeric") from exc
        if not math.isfinite(value):
            raise ValueError("score must be finite")
        groups.setdefault(group, []).append(value)
    if len(groups) < 2 or any(len(values) < 2 for values in groups.values()):
        raise ValueError("at least two groups with two scores each are required")
    if len(groups) > 32:
        raise ValueError("at most 32 groups permitted for bounded comparisons")
    if sum(map(len, groups.values())) > 10000:
        raise ValueError("too many observations for bounded bootstrap")
    summaries = {}
    for index, name in enumerate(sorted(groups)):
        scores = groups[name]
        low, high, _ = bootstrap_ci_mean(
            scores, alpha=alpha, n_bootstrap=BOOTSTRAPS, random_state=SEED + index
        )
        summaries[name] = {
            "n": len(scores),
            "mean": mean(scores),
            "sample_std": stdev(scores),
            "bootstrap_ci": [low, high],
        }
    comparisons = []
    for index, (left, right) in enumerate(combinations(sorted(groups), 2)):
        estimate, low, high = bootstrap_ci_diff_means(
            groups[left],
            groups[right],
            alpha=alpha,
            n_bootstrap=BOOTSTRAPS,
            random_state=SEED + 1000 + index,
        )
        comparisons.append(
            {
                "left": left,
                "right": right,
                "estimate_right_minus_left": estimate,
                "bootstrap_ci": [low, high],
            }
        )
    record = {
        "schema": SCHEMA,
        "method": METHOD,
        "semantics_status": SEMANTICS,
        "source_sha256": data_sha,
        "alpha": alpha,
        "n_bootstrap": BOOTSTRAPS,
        "random_state": SEED,
        "groups": summaries,
        "comparisons": comparisons,
        "merge_admission": "HOLD",
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }
    record["receipt_sha256"] = digest(record)
    target = destination / f"dataset-{data_sha[:12]}" / "phase2_metadata.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--dow-root", type=Path, required=True)
    parser.add_argument("--alpha", type=float, required=True)
    parser.add_argument("--mode", choices=["csv"], required=True)
    args = parser.parse_args(argv)
    try:
        path = measure(args.results_dir, args.dow_root, args.alpha)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(2, f"Phase 2 input contract failed: {exc}\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

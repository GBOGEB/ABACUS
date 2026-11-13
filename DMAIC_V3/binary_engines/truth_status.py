"""Truth status of inventoried binaries against pinned hashes: a pure matcher. No git, no subprocess.

Is a file the authority, a copy held for custody, an older version, or nothing anyone pinned? The pins come from
outside: a map ``{sha256: ["<repo>:<path>", ...]}`` of the hashes that repository manifests (releases, canonical
and SSOT files, checksums, receipts) pin, collected by a separate node that reads those manifests with git. This
module only matches inventory rows against that map.

  AUTHORITATIVE   the bytes are pinned by at least one canonical manifest (a pin outside the custody paths)
  RECORDED        the bytes are pinned only under custody paths (archive, incubator, history, receipt, triage/)
  SUPERSEDED      not pinned, and an older member of its family: a newer version exists
  STALE_RELEVANT  not pinned, the newest of its family, and another member of the family is pinned
  UNPINNED        neither it nor its family is pinned: information, not truth, until a repository owns it

    python -I -X utf8 DMAIC_V3/binary_engines/truth_status.py --pins <pin map.json> [--out <file>]
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from collections.abc import Collection, Iterable, Mapping
from pathlib import Path

AUTHORITATIVE, RECORDED, SUPERSEDED = "AUTHORITATIVE", "RECORDED", "SUPERSEDED"
STALE_RELEVANT, UNPINNED = "STALE_RELEVANT", "UNPINNED"
STATUSES = (AUTHORITATIVE, RECORDED, STALE_RELEVANT, SUPERSEDED, UNPINNED)
CUSTODY_RX = re.compile(
    r"(?i)archive|incubator|history|receipt|triage/"
)  # custody, not authority
SCHEMA = "gbogeb.estate.truth_status/0.1"
_SHA256_RX = re.compile(r"[0-9a-f]{64}")


def row_key(row: Mapping) -> tuple:
    """Identity of an inventory row across roots: (root id, name)."""
    return row.get("root_id"), row["name"]


def load_pins(data: object) -> dict[str, list[str]]:
    """Validate a pin map and return it with lower-case hashes; raises ValueError on anything else (fail closed).

    Accepts the map itself, ``{sha256: [locator, ...]}``, or an object ``{"pins": {...}, "heads": {...}}``.
    """
    pins = (
        data.get("pins")
        if isinstance(data, dict) and isinstance(data.get("pins"), dict)
        else data
    )
    if not isinstance(pins, dict):
        raise ValueError('a pin map is a JSON object {sha256: ["repo:path", ...]}')
    out: dict[str, list[str]] = {}
    for sha, where in pins.items():
        key = sha.lower() if isinstance(sha, str) else sha
        if not isinstance(key, str) or not _SHA256_RX.fullmatch(key):
            raise ValueError(f"pin key is not a sha256: {sha!r}")
        if (
            not isinstance(where, list)
            or not where
            or not all(isinstance(w, str) and w for w in where)
        ):
            raise ValueError(
                f'pin {sha} needs a non-empty list of "repo:path" locators'
            )
        bucket = out.setdefault(
            key, []
        )  # an upper- and a lower-case key for one hash merge
        bucket.extend(w for w in where if w not in bucket)
    return out


def classify(
    rows: Iterable[Mapping],
    pins: Mapping[str, list[str]],
    family_tips: Collection[tuple] | None = None,
) -> list[dict]:
    """One truth record per row, in row order.

    ``rows`` are inventory rows (root_inventory_final.json) with ``name``, ``type``, ``family``, ``sha256`` and
    usually ``root_id``, ``family_tip``, ``epic_final`` and ``age_days``. ``pins`` is a validated pin map.
    ``family_tips``, when given, is the set of ``row_key`` values that are the newest of their family and replaces
    each row's own ``family_tip``; a row without either counts as a tip.
    """
    rows = list(rows)
    pinned_families = {
        (r["type"], r["family"])
        for r in rows
        if r.get("sha256") and r["sha256"] in pins
    }
    out = []
    for r in rows:
        where = list(pins.get(r["sha256"], [])) if r.get("sha256") else []
        canonical = [w for w in where if not CUSTODY_RX.search(w)]
        tip = (
            row_key(r) in family_tips
            if family_tips is not None
            else r.get("family_tip", True)
        )
        if canonical:
            truth = AUTHORITATIVE
        elif where:
            truth = RECORDED
        elif not tip:
            truth = SUPERSEDED
        elif (r["type"], r["family"]) in pinned_families:
            truth = STALE_RELEVANT
        else:
            truth = UNPINNED
        out.append(
            {
                "root": r.get("root_id"),
                "name": r["name"],
                "type": r["type"],
                "epic": r.get("epic_final"),
                "truth": truth,
                "pinned_in": (canonical + [w for w in where if w not in canonical])[:3],
                "age_days": r.get("age_days"),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--pins",
        required=True,
        type=Path,
        help="pin map JSON from the pin-collection node",
    )
    ap.add_argument(
        "--out", type=Path, help="default: <ESTATE_HOME>/deep/authority.json"
    )
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from estate_spec import ESTATE, REAL_ROOTS, inv_dir

    raw = a.pins.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    pins = load_pins(data)
    heads = (
        data.get("heads", {})
        if isinstance(data, dict) and isinstance(data.get("pins"), dict)
        else {}
    )
    rows = []
    for rid in REAL_ROOTS:
        final = inv_dir(rid) / "root_inventory_final.json"
        if final.exists():
            rows += [dict(r, root_id=rid) for r in json.loads(final.read_text("utf-8"))]
    out = classify(rows, pins)
    dest = a.out or ESTATE / "deep" / "authority.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": SCHEMA,
        "pins_sha256": hashlib.sha256(raw).hexdigest(),
        "heads": heads,
        "pinned_hashes": len(pins),
        "rows": out,
    }
    dest.write_text(json.dumps(report, indent=1, ensure_ascii=False), "utf-8")
    counts = collections.Counter((r["root"], r["truth"]) for r in out)
    print(f"pinned sha256 values: {len(pins)}  rows: {len(out)}  -> {dest}")
    for (root, truth), n in sorted(counts.items()):
        print(f"  {root:5} {truth:15} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

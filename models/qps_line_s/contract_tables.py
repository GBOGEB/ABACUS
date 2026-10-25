"""Upstream drift check for the vendored contract extracts.

docs/qps_line_s_recovery/ holds verbatim copies of parts of the
cryoplant-project contract extraction (Addendum II rev 146):

- addendum2_rev146_tables_27_29.json: App. 11.2 Tables 27-29, bound to
  ssot_tables.py by tests/test_ssot_tables_contract.py;
- addendum2_rev146_rtm_292_293_061.json: RTM-292, RTM-293, RTM-061 and
  Table 7, bound to the Line S envelope by tests/test_rtm292_contract.py.

This module binds each copy to a fresh upstream contract file, so a new
contract revision fails here instead of passing silently.

Run:  python -m models.qps_line_s.contract_tables --contract <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

VENDORED_DIR = Path(__file__).resolve().parents[2] / "docs" / "qps_line_s_recovery"
VENDORED_PATH = VENDORED_DIR / "addendum2_rev146_tables_27_29.json"
RTM_VENDORED_PATH = VENDORED_DIR / "addendum2_rev146_rtm_292_293_061.json"
VENDORED_PATHS = (VENDORED_PATH, RTM_VENDORED_PATH)
TABLE_PREFIXES = ("Table 27.", "Table 28.", "Table 29.")


def load_vendored(path: Path = VENDORED_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_tables(
    contract: dict, prefixes: tuple[str, ...] = TABLE_PREFIXES
) -> list[dict]:
    """Tables from a contract extraction, by caption prefix."""
    return [t for t in contract["tables"] if (t["caption"] or "").startswith(prefixes)]


def extract_requirements(contract: dict, ids: list[str]) -> list[dict]:
    """Requirement records in the given ID order; missing IDs are skipped."""
    requirements = contract.get("requirements", {})
    return [requirements[i] for i in ids if i in requirements]


def tables_sha256(tables: list[dict]) -> str:
    canonical = json.dumps(
        tables, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def upstream_drift(contract_path: Path, vendored: dict) -> list[str]:
    """Differences between an upstream contract file and one vendored copy."""
    raw = contract_path.read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    source = vendored["source"]
    problems = []
    digest = hashlib.sha256(raw).hexdigest()
    if digest != source["sha256"]:
        problems.append(f"contract sha256 {digest} != vendored {source['sha256']}")
    revision = contract["source"]["docx_core"]["revision"]
    if revision != source["contract_docx_revision"]:
        problems.append(
            f"contract revision {revision} != vendored "
            f"{source['contract_docx_revision']}"
        )
    label = vendored.get("label", "Tables 27-29")
    prefixes = tuple(vendored.get("table_captions", TABLE_PREFIXES))
    if tables_sha256(extract_tables(contract, prefixes)) != vendored["tables_sha256"]:
        problems.append(
            f"{label} differ from the vendored rows: re-extract them and "
            "re-check the bound model inputs"
        )
    ids = vendored.get("requirement_ids", [])
    if ids:
        found = extract_requirements(contract, ids)
        missing = [i for i in ids if i not in contract.get("requirements", {})]
        if missing:
            problems.append(f"requirements missing upstream: {', '.join(missing)}")
        elif tables_sha256(found) != vendored["requirements_sha256"]:
            problems.append(
                f"requirements {', '.join(ids)} differ from the vendored records"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument(
        "--vendored",
        type=Path,
        action="append",
        help="vendored extract to check (repeatable; default: all)",
    )
    args = parser.parse_args(argv)
    failed = False
    for path in args.vendored or VENDORED_PATHS:
        problems = upstream_drift(args.contract, load_vendored(path))
        for problem in problems:
            print(f"DRIFT: {path.name}: {problem}")
        if not problems:
            print(f"OK: upstream contract matches {path.name}")
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

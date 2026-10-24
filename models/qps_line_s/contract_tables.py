"""Upstream drift check for the vendored contract Tables 27-29.

docs/qps_line_s_recovery/addendum2_rev146_tables_27_29.json is a verbatim
copy of three tables from the cryoplant-project contract extraction.
tests/test_ssot_tables_contract.py binds ssot_tables.py to that copy; this
module binds the copy to a fresh upstream contract file, so a new contract
revision fails here instead of passing silently.

Run:  python -m models.qps_line_s.contract_tables --contract <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

VENDORED_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "qps_line_s_recovery"
    / "addendum2_rev146_tables_27_29.json"
)
TABLE_PREFIXES = ("Table 27.", "Table 28.", "Table 29.")


def load_vendored(path: Path = VENDORED_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_tables(contract: dict) -> list[dict]:
    """Tables 27-29 from a contract extraction, by caption prefix."""
    return [
        t for t in contract["tables"] if (t["caption"] or "").startswith(TABLE_PREFIXES)
    ]


def tables_sha256(tables: list[dict]) -> str:
    canonical = json.dumps(
        tables, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def upstream_drift(contract_path: Path, vendored: dict) -> list[str]:
    """Differences between an upstream contract file and the vendored copy."""
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
    tables = extract_tables(contract)
    if tables_sha256(tables) != vendored["tables_sha256"]:
        problems.append(
            "Tables 27-29 differ from the vendored rows: re-extract them and "
            "re-check ssot_tables.py"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--vendored", type=Path, default=VENDORED_PATH)
    args = parser.parse_args(argv)
    problems = upstream_drift(args.contract, load_vendored(args.vendored))
    for problem in problems:
        print(f"DRIFT: {problem}")
    if not problems:
        print("OK: upstream contract matches the vendored Tables 27-29")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

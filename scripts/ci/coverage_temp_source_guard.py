"""Qualify deleted tempfile localpkg fixtures before rendering coverage.

Only an exact, absent /tmp/tmp*/localpkg/__init__.py fixture may be omitted
from coverage *reports*. Raw coverage data and actual source remain unchanged.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

from coverage import Coverage

_TEMP_NAME = re.compile(r"tmp[a-zA-Z0-9_-]+\Z")


def in_dir(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def qualify_fixture(path: Path, root: Path, temp_root: Path) -> bool:
    if in_dir(path, root) or path.exists():
        return False
    try:
        parts = path.relative_to(temp_root).parts
    except ValueError:
        return False
    return (
        len(parts) == 3
        and bool(_TEMP_NAME.fullmatch(parts[0]))
        and parts[1:] == ("localpkg", "__init__.py")
    )


def reconcile(data_file: str, root: str, temp_dir: str, receipt: str,
              xml: str, coverage_json: str) -> dict:
    root_path = Path(root).resolve()
    temp_root = Path(temp_dir).resolve()
    if not root_path.is_dir() or not (root_path / "pyproject.toml").is_file():
        raise ValueError("expected repository root with pyproject.toml")
    if in_dir(root_path, temp_root):
        raise ValueError("checkout inside temp dir cannot be source-qualified")

    cov = Coverage(data_file=data_file, config_file=str(root_path / "pyproject.toml"))
    cov.load()
    data = cov.get_data()
    files = sorted(data.measured_files())
    missing = [Path(f).absolute() for f in files if not Path(f).is_file()]
    approved, rejected = [], []
    for path in missing:
        if qualify_fixture(path, root_path, temp_root):
            approved.append(str(path))
        else:
            rejected.append(str(path))
    result = {
        "schema": "abacus-coverage-missing-source/1",
        "status": "HOLD" if rejected else "PASS",
        "measured_before": len(files),
        "approved_deleted_fixture": approved,
        "rejected_missing_source": rejected,
    }
    Path(receipt).parent.mkdir(parents=True, exist_ok=True)
    if rejected:
        Path(receipt).write_text(json.dumps(result, indent=2) + "\n")
        raise ValueError("missing non-fixture source: " + ", ".join(rejected))

    # Do not purge or rewrite raw .coverage: file-set integrity stays testable.
    if set(data.measured_files()) != set(files):
        raise ValueError("raw coverage data unexpectedly changed")
    omit = list(cov.get_option("run:omit") or []) + approved
    try:
        Path(xml).parent.mkdir(parents=True, exist_ok=True)
        Path(coverage_json).parent.mkdir(parents=True, exist_ok=True)
        cov.xml_report(outfile=xml, omit=omit)
        cov.json_report(outfile=coverage_json, omit=omit, show_contexts=True)
        cov.report(omit=omit)
    except Exception as exc:
        result["status"] = "HOLD"
        result["report_error"] = str(exc)
        Path(receipt).write_text(json.dumps(result, indent=2) + "\n")
        raise
    result["measured_after"] = len(data.measured_files())
    result["qualified_report_omit"] = approved
    Path(receipt).write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", default=".coverage")
    parser.add_argument("--root", default=".")
    parser.add_argument("--temp-dir", default=tempfile.gettempdir())
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--xml", required=True)
    parser.add_argument("--coverage-json", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(reconcile(args.data_file, args.root, args.temp_dir,
                                   args.receipt, args.xml, args.coverage_json)))
        return 0
    except (ValueError, OSError) as exc:
        print("::error::Coverage source admission HOLD: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Read-only, fail-closed pytest marker configuration validation.

pytest.ini is the canonical marker source. A secondary pyproject marker
declaration, when present, must match it exactly. Absent secondary configuration
is reported as single-source validation, never as synchronization evidence.
"""
from __future__ import annotations

import argparse
import configparser
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9/3.10: declared requirements-dev tomli
    import tomli as tomllib


ROOT = Path(__file__).resolve().parent
MARKER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _markers(entries, *, owner):
    if isinstance(entries, str):
        entries = entries.splitlines()
    if not isinstance(entries, (list, tuple)):
        raise ValueError(f"{owner}: marker definitions must be a string or list")
    found = {}
    for value in entries:
        if not isinstance(value, str):
            raise ValueError(f"{owner}: non-string marker declaration")
        value = value.strip()
        if not value or value.startswith("#"):
            continue
        label = value.split(":", 1)[0].split("(", 1)[0].strip()
        if not MARKER.fullmatch(label):
            raise ValueError(f"{owner}: invalid marker name {label!r}")
        if label in found:
            raise ValueError(f"{owner}: duplicate marker {label}")
        found[label] = " ".join(value.split())
    if not found:
        raise ValueError(f"{owner}: empty marker declaration set")
    return found


def validate(root=ROOT):
    root = Path(root)
    ini = root / "pytest.ini"
    if not ini.is_file():
        raise ValueError("Missing canonical pytest.ini")
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    parser.optionxform = str
    with ini.open(encoding="utf-8") as stream:
        parser.read_file(stream)
    if not parser.has_section("pytest") or not parser.has_option("pytest", "markers"):
        raise ValueError("Canonical pytest.ini has no [pytest] markers")
    canonical = _markers(parser.get("pytest", "markers"), owner="pytest.ini")

    other = root / "pyproject.toml"
    secondary = None
    if other.is_file():
        with other.open("rb") as stream:
            cfg = tomllib.load(stream)
        tool = cfg.get("tool", {})
        opts = tool.get("pytest", {}).get("ini_options", {})
        if opts is not None and not isinstance(opts, dict):
            raise ValueError("Malformed pyproject pytest ini_options")
        if opts and "markers" in opts:
            secondary = _markers(opts["markers"], owner="pyproject.toml")
            if secondary != canonical:
                missing = sorted(set(canonical) - set(secondary))
                extra = sorted(set(secondary) - set(canonical))
                changed = sorted(k for k in set(canonical) & set(secondary)
                                 if canonical[k] != secondary[k])
                raise ValueError(
                    f"Pytest marker configuration drift: missing={missing} "
                    f"extra={extra} changed={changed}"
                )
    return {
        "schema": "abacus.pytest-markers-validation.v1",
        "status": "SYNCHRONIZED" if secondary is not None
                  else "SINGLE_CANONICAL_SOURCE_VALIDATED",
        "canonical": "pytest.ini",
        "marker_count": len(canonical),
        "secondary_config": "pyproject.toml" if secondary is not None
                            else "NOT_DECLARED",
        "source_mutation": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Read-only validation")
    parser.parse_args(argv)
    try:
        print(json.dumps(validate(), sort_keys=True))
    except (ValueError, OSError, configparser.Error, tomllib.TOMLDecodeError) as exc:
        print(f"PYTEST_MARKER_SYNC_FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Canonical ABACUS/DMAIC package entrypoint."""

from __future__ import annotations

import argparse
import json

from .product_version import ABACUS_VERSION
from .config import VERSION as ENGINE_VERSION
from .self_smoke import run_self_smoke


def main() -> int:
    parser = argparse.ArgumentParser(prog="abacus")
    parser.add_argument("command", nargs="?", default="version", choices=("version", "self-smoke"))
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.command == "version":
        payload = {"product": "ABACUS", "product_version": ABACUS_VERSION, "engine": "DMAIC", "engine_version": ENGINE_VERSION}
        print(json.dumps(payload, sort_keys=True) if args.as_json else f"ABACUS {ABACUS_VERSION} | DMAIC engine {ENGINE_VERSION}")
        return 0

    receipt = run_self_smoke()
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

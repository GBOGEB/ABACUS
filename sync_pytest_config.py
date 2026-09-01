"""Compatibility shim for legacy CI workflow step."""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Pytest config sync shim")
    parser.add_argument("--dry-run", action="store_true", help="No-op dry run")
    parser.parse_args()
    return 0


if __name__ == "__main__":
    sys.exit(main())

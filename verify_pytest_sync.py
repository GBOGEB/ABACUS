"""Legacy CI entrypoint, delegating to fail-closed canonical marker validation."""

from __future__ import annotations

import sys

from sync_pytest_config import main as sync_main


def main():
    return sync_main(["--dry-run"])


if __name__ == "__main__":
    sys.exit(main())

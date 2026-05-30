"""Module entrypoint for `python -m qplant_presentation_engine`."""

from .runtime import run_runtime


def main() -> int:
    """Run runtime smoke path and print status report."""
    exit_code, report, _metadata = run_runtime()
    for line in report:
        print(line)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


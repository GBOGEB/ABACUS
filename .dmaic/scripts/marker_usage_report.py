"""Generate a minimal marker usage report artifact for CI compatibility."""

from pathlib import Path


def main() -> None:
    report_path = Path(".dmaic/reports/marker_usage_report.txt")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("Marker usage report generation is currently delegated to CI hooks.\n", encoding="utf-8")


if __name__ == "__main__":
    main()

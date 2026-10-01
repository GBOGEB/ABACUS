from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "DMAIC_V3" / "requirements.txt"
GENERATORS = ROOT / "DMAIC_V3" / "generators" / "requirements.txt"


def _markdown_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("markdown>=")
    ]


def test_markdown_311_is_not_selected_for_python_310():
    assert _markdown_lines(CANONICAL) == [
        "markdown>=3.3.0,<3.11; python_version < '3.11'",
        "markdown>=3.11,<4.0.0; python_version >= '3.11'",
    ]
    assert _markdown_lines(GENERATORS) == [
        "markdown>=3.3.0,<3.11; python_version < '3.11'",
        "markdown>=3.11; python_version >= '3.11'",
    ]

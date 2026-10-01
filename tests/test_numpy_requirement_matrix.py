from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "DMAIC_V3" / "requirements.txt"
GENERATORS = ROOT / "DMAIC_V3" / "generators" / "requirements.txt"


def _numpy_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("numpy>=")
    ]


def test_canonical_numpy_requirements_preserve_python_compatibility_matrix():
    generator_lines = _numpy_lines(GENERATORS)
    canonical_lines = _numpy_lines(CANONICAL)

    assert len(generator_lines) == 5
    assert len(canonical_lines) == 5

    expected = [
        line.replace(";", ",<3.0.0;")
        for line in generator_lines
    ]
    assert canonical_lines == expected


def test_numpy_25_is_not_selected_for_python_311():
    lines = _numpy_lines(CANONICAL)

    py311 = [
        line
        for line in lines
        if "python_version >= '3.11'" in line
        and "python_version < '3.12'" in line
    ]
    py312 = [
        line
        for line in lines
        if "python_version >= '3.12'" in line
    ]

    assert py311 == [
        "numpy>=2.4.6,<3.0.0; python_version >= '3.11' "
        "and python_version < '3.12'"
    ]
    assert py312 == [
        "numpy>=2.5.3,<3.0.0; python_version >= '3.12'"
    ]



def _markdown_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("markdown>=")
    ]


def test_markdown_311_is_not_selected_for_python_310():
    canonical = _markdown_lines(CANONICAL)
    generators = _markdown_lines(GENERATORS)

    assert canonical == [
        "markdown>=3.3.0,<3.11; python_version < '3.11'",
        "markdown>=3.11,<4.0.0; python_version >= '3.11'",
    ]
    assert generators == [
        "markdown>=3.3.0,<3.11; python_version < '3.11'",
        "markdown>=3.11; python_version >= '3.11'",
    ]

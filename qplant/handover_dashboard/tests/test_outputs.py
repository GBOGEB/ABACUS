from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class StrictHTMLParser(HTMLParser):
    pass


def test_all_expected_files_exist():
    expected = [
        DOCS / "index.html",
        DOCS / "index_v3_1.html",
        DOCS / "manifest.json",
        DOCS / "backlog.json",
        DOCS / "changelog.md",
        ROOT / "setup.sh",
        ROOT / "build.sh",
        ROOT / "validate.sh",
        ROOT / "package.sh",
    ]
    for path in expected:
        assert path.exists(), f"Missing expected file: {path}"

    charts = list((DOCS / "visualizations_v3").glob("*.html"))
    assert len(charts) >= 15

    slides_text = (DOCS / "index_v3_1.html").read_text(encoding="utf-8", errors="ignore")
    slide_count = slides_text.count('class="slide')
    assert slide_count >= 40


def test_html_renders():
    html_files = [DOCS / "index.html", DOCS / "index_v3_1.html", DOCS / "dashboard.html"]
    parser = StrictHTMLParser()
    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        assert "<html" in content.lower()
        assert "</html>" in content.lower()
        parser.feed(content)


def test_json_valid():
    json_files = [
        DOCS / "manifest.json",
        DOCS / "backlog.json",
        ROOT / "data" / "standards_compliance.json",
        ROOT / "data" / "helium_properties.json",
        ROOT / "data" / "compressor_specs.json",
    ]
    for path in json_files:
        with path.open("r", encoding="utf-8") as f:
            json.load(f)

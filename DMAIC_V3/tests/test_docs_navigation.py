from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"


def test_dashboard_pages_include_cross_page_navigation_links():
    expected_links = (
        'href="./"',
        'href="cryo/"',
        'href="12-cluster/"',
        'href="dow/"',
        'href="testing/"',
        'href="tools/"',
        'href="versions/"',
    )

    for page in ("dashboard.html", "deep_analysis_dashboard.html"):
        html = (DOCS_ROOT / page).read_text(encoding="utf-8")
        for link in expected_links:
            assert link in html, f"Missing {link} in {page}"

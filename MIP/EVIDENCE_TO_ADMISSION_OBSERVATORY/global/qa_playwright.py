#!/usr/bin/env python3
"""W39 deterministic browser QA of the source-bound global DOV projection.

Network requests are intercepted with fixture response values. They exercise
the refresh interaction but ARE NOT native GitHub observations. This runner
never opens a GitHub URL and cannot grant admission or publish Pages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
VIEWPORTS = (("desktop", 1440, 1000), ("laptop", 1280, 800), ("mobile", 390, 844))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def browser_binary() -> str:
    for candidate in ("google-chrome", "chromium", "chromium-browser"):
        executable = shutil.which(candidate)
        if executable:
            return executable
    raise RuntimeError("No installed Chromium/Chrome binary; visual QA must FAIL")


def fixture_payload(request_url: str, ledger: dict) -> dict:
    parts = urlsplit(request_url)
    path = parts.path
    if parts.scheme != "https" or parts.netloc != "api.github.com":
        raise AssertionError("Unexpected external request")
    if path.startswith("/repos/") and path.endswith("/branches/main"):
        repo = "/".join(path.split("/")[2:4])
        matching = next((x for x in ledger["repos"] if x["repo"] == repo), None)
        if matching is None:
            raise AssertionError("Unexpected branch lookup")
        return {"commit": {"sha": matching["main_sha"]}}
    if path.startswith("/repos/GBOGEB/ABACUS/actions/runs/"):
        historical = ledger["governance"]["previous_native_run"]
        if path.split("/")[-1] != str(historical["run_id"]):
            raise AssertionError("Unexpected governance run")
        return {
            "head_sha": historical["head_sha"],
            "conclusion": "failure",
            "status": "completed",
        }
    if path == "/search/issues":
        q = parse_qs(parts.query).get("q", [""])[0]
        repo = next((x for x in ledger["repos"] if "repo:" + x["repo"] in q), None)
        if repo is None:
            raise AssertionError("Unexpected issue-search repository")
        patterns = {
            "issues_open": "is:issue state:open",
            "issues_closed": "is:issue state:closed",
            "prs_open": "is:pr state:open",
            "prs_closed_unmerged": "is:pr state:closed is:unmerged",
            "prs_merged": "is:pr is:merged",
        }
        key = next((name for name, term in patterns.items() if term in q), None)
        if key is None:
            raise AssertionError("Unexpected issue-search cohort")
        return {
            "total_count": repo[key] + (1 if key == "issues_open" else 0),
            "incomplete_results": False,
        }
    raise AssertionError("Unregistered GitHub API route: " + path)


def wait_for_status_text(page, expected: str, attempts: int = 160) -> None:
    """Poll visible text without page eval: CSP intentionally excludes unsafe-eval."""
    for _ in range(attempts):
        current = page.locator("#refresh-result").inner_text()
        if expected in current:
            return
        page.wait_for_timeout(100)
    raise AssertionError(
        "Refresh status did not include "
        + expected
        + ": "
        + page.locator("#refresh-result").inner_text()
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "w39_qa_receipts")
    args = ap.parse_args()
    ledger = json.loads((HERE / "ledger.json").read_text(encoding="utf-8"))
    html = HERE / "index.html"
    args.out.mkdir(parents=True, exist_ok=True)
    total_requests = []
    visual = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=browser_binary(),
            args=["--no-sandbox", "--disable-gpu"],
        )
        try:
            for name, width, height in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": height})
                errors = []
                requests = []
                page.on("pageerror", lambda ex: errors.append("PAGE: " + str(ex)))
                page.on(
                    "console",
                    lambda m: (
                        errors.append("CONSOLE: " + m.text)
                        if m.type == "error"
                        else None
                    ),
                )

                def intercept(route):
                    if route.request.method != "GET":
                        raise AssertionError(
                            "Dashboard attempted non-GET GitHub access"
                        )
                    requests.append(route.request.url)
                    data = fixture_payload(route.request.url, ledger)
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        headers={"access-control-allow-origin": "*"},
                        body=json.dumps(data),
                    )

                page.route("https://api.github.com/**", intercept)
                page.goto(html.as_uri(), wait_until="load")
                page.locator("h1").wait_for()
                assert "Global Mission Control" in page.locator("h1").inner_text()
                assert page.locator("#localTargets").inner_text() == "4/4"
                assert page.locator("#classified").inner_text() == "201/201"
                assert page.locator("#globalCoverage").inner_text() == "97.79%"

                assert page.locator("#taxCards details").count() == len(
                    ledger["taxonomy"]["terms"]
                )
                page.locator("#taxSearch").fill("3P-RAL")
                assert page.locator("#taxCards details").count() >= 1
                page.locator("#taxSearch").fill("unlikely_moniker_no_match")
                assert page.locator("#taxCards details").count() == 0
                page.locator("#taxSearch").fill("")
                page.locator("#taxFamily").select_option("cycle")
                assert page.locator("#taxCards details").count() == len(
                    [
                        term
                        for term in ledger["taxonomy"]["terms"]
                        if term["family"] == "cycle"
                    ]
                )
                page.locator("#taxFamily").select_option("all")
                assert page.locator("#taxCards details").count() == len(
                    ledger["taxonomy"]["terms"]
                )
                page.locator("#taxCards details").first.locator("summary").click()
                assert (
                    page.locator("#taxCards details")
                    .first.locator('a[href^="https://github.com/"]')
                    .count()
                    == 1
                )
                assert not requests, "Unexpected autonomous/background API fetch"
                for anchor in page.locator('a[href^="#"]').all():
                    selector = anchor.get_attribute("href")
                    assert page.locator(selector).count() > 0, (
                        "Missing fragment " + selector
                    )
                assert page.locator("img:not([complete])").count() == 0
                page.locator('button[data-lens="governance"]').click()
                assert (
                    page.locator('button[data-lens="governance"]').get_attribute(
                        "aria-pressed"
                    )
                    == "true"
                )
                assert page.locator('#spine path[data-lens="native"]').first.evaluate(
                    "(x) => x.classList.contains('hide')"
                )
                page.locator('button[data-lens="all"]').click()
                assert not page.locator(
                    '#spine path[data-lens="native"]'
                ).first.evaluate("(x) => x.classList.contains('hide')")
                if name == "desktop":
                    page.locator("#status-refresh").click()
                    wait_for_status_text(page, "4/4 responses", attempts=120)
                    assert (
                        "W36 historical=failure"
                        in page.locator("#refresh-result").inner_text()
                    )
                    page.locator("#full-refresh").click()
                    wait_for_status_text(page, "15 searches complete", attempts=200)
                    assert (
                        page.locator("#repoTotals td.num").first.inner_text() == "109"
                    )
                    assert len(requests) == 19
                extent = page.locator("html").evaluate("""(element) => ({
                    doc: element.scrollWidth,
                    body: document.body.scrollWidth,
                    viewport: element.clientWidth
                })""")
                assert (
                    extent["doc"] <= extent["viewport"] + 1
                ), "Document horizontal overflow " + str(extent)
                assert (
                    extent["body"] <= extent["viewport"] + 1
                ), "Body horizontal overflow " + str(extent)
                assert not errors, errors
                filename = args.out / ("w39-" + name + ".png")
                page.screenshot(path=str(filename), full_page=True)
                visual.append(
                    {
                        "viewport": name,
                        "width": width,
                        "height": height,
                        "screenshot": filename.name,
                        "sha256": digest(filename),
                        "document_overflow": False,
                        "console_errors": 0,
                        "page_errors": 0,
                        "api_get_requests": len(requests),
                    }
                )
                total_requests.extend(requests)
                page.close()
        finally:
            browser.close()

    result = {
        "schema": "codepurple.w39.browser_qa.v1",
        "scope": "LOCAL_BROWSER_INTERACTION_AND_MOCKED_PUBLIC_API_ONLY",
        "html_sha256": digest(html),
        "ledger_sha256": digest(HERE / "ledger.json"),
        "viewports": visual,
        "actual_github_api_responses_used": False,
        "mutating_requests": 0,
        "admission": "HOLD",
        "global_control": False,
        "release_qualified": False,
    }
    (args.out / "W39_BROWSER_QA.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "result": "PASS",
                "viewports": len(visual),
                "mocked_api_requests": len(total_requests),
                "ledger_sha256": result["ledger_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

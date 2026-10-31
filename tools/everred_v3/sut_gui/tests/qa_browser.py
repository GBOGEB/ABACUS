from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHA = "8" * 40
ABACUS = "e" * 40
CODEX = "3" * 40
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(i, name, status, conclusion=None):
    return {
        "id": i,
        "name": name,
        "head_sha": SHA,
        "status": status,
        "conclusion": conclusion,
        "html_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{i}",
        "created_at": NOW,
    }


RUNS = [
    run(100, "CODE PURPLE SUT GUI Contract", "completed", "success"),
    run(101, "MIP B0 Test Admission and Coverage Evidence", "completed", "success"),
    run(102, "EVERRED V3 Governed Control Plane", "completed", "failure"),
]
RUNS += [run(200 + i, "Queued workflow " + str(i), "queued") for i in range(18)]
RUNS += [run(304, "Format Check", "in_progress")]
assert len(RUNS) == 22


def route_handler(route):
    url = route.request.url
    payload = {}
    if "/branches/main" in url:
        payload = {
            "commit": {"sha": CODEX if "/CODEX/" in url else ABACUS},
            "protected": False,
        }
    elif "/rulesets/" in url:
        payload = {"id": 24494381, "enforcement": "active", "rules": []}
    elif "/pulls/1956/reviews" in url:
        payload = []
    elif "/pulls/1956" in url:
        payload = {
            "state": "open",
            "draft": True,
            "merged": False,
            "head": {"sha": SHA},
            "user": {"login": "author"},
        }
    elif "/pulls/1951" in url:
        payload = {
            "state": "closed",
            "draft": False,
            "merged": True,
            "head": {"sha": ABACUS},
            "user": {"login": "author"},
        }
    elif "/actions/runs/102/jobs" in url:
        payload = {
            "total_count": 1,
            "jobs": [
                {
                    "id": 900,
                    "name": "test matrix 3.10",
                    "conclusion": "failure",
                    "html_url": "https://github.com/GBOGEB/ABACUS/actions/runs/102/job/900",
                    "steps": [
                        {"name": "Checkout", "conclusion": "success"},
                        {"name": "Verify Black/isort styles", "conclusion": "failure"},
                    ],
                }
            ],
        }
    elif "/actions/runs?" in url:
        payload = {"total_count": 22, "workflow_runs": RUNS}
    else:
        raise AssertionError("Unexpected API path " + url)
    route.fulfill(
        status=200,
        content_type="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
        body=json.dumps(payload),
    )


def mock_live():
    return {
        "schema": "code-purple.live.v2",
        "collected_at": NOW,
        "source": "GITHUB_API_TEST_FIXTURE",
        "repositories": {
            "GBOGEB/ABACUS": {"sha": ABACUS, "protected": False},
            "GBOGEB/CODEX": {"sha": CODEX, "protected": False},
        },
        "ruleset": {"rule_count": 0, "enforcement": "active"},
        "prs": {
            "1956": {
                "state": "open",
                "draft": True,
                "merged": False,
                "sha": SHA,
                "author": "author",
            },
            "1951": {"state": "closed", "merged": True, "sha": ABACUS},
        },
        "independent_review": "NOT_OBSERVED",
        "errors": [],
        "ci": {
            "status": "OBSERVED",
            "source_sha": SHA,
            "total_count": 22,
            "sample_complete": True,
            "first_red_completeness": "COMPLETE",
            "runs": [{**row, "url": row["html_url"]} for row in RUNS],
            "metrics": {
                "total_observed": 22,
                "terminal": 3,
                "success": 2,
                "failure": 1,
                "queued": 18,
                "in_progress": 1,
                "cancelled_or_other": 0,
            },
            "first_reds": [
                {
                    "workflow": "EVERRED V3 Governed Control Plane",
                    "run_id": 102,
                    "job_id": 900,
                    "job": "test matrix 3.10",
                    "step": "Verify Black/isort styles",
                    "sha": SHA,
                    "url": "https://github.com/GBOGEB/ABACUS/actions/runs/102/job/900",
                    "classification": "UNCLASSIFIED",
                    "root_id": None,
                }
            ],
        },
        "collection": "COMPLETE",
        "merge_authorized": False,
        "security_waiver": False,
        "authority_transfer": False,
    }


qa = {
    "schema": "code-purple.browser-qa.v2",
    "source_mode": "GITHUB_API_MOCK_FOR_BROWSER_PRESENTATION_ONLY",
    "captured_at": NOW,
    "viewports": {},
    "model_checks": {},
    "errors": [],
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(
    ("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT))
)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path="/usr/bin/chromium",
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    for key, width, height in [
        ("desktop", 1440, 1000),
        ("laptop", 1280, 800),
        ("mobile", 390, 844),
    ]:
        page = browser.new_page(
            viewport={"width": width, "height": height}, device_scale_factor=1
        )
        errors = []
        page.on("pageerror", lambda e: errors.append("page:" + str(e)))
        page.on(
            "console",
            lambda e: errors.append("console:" + e.text) if e.type == "error" else None,
        )
        page.route("https://api.github.com/**", route_handler)
        page.set_content(
            (ROOT / "index.html").read_text(encoding="utf-8"), wait_until="load"
        )
        page.wait_for_function(
            "document.getElementById('terminal-percent').textContent === '13.6%'",
            timeout=15000,
        )
        assert page.locator("#red-count").inner_text() == "1"
        assert page.locator("#queue-count").inner_text() == "19"
        assert page.locator("#success-percent").inner_text() == "66.7%"
        assert page.locator("#abacus-state").inner_text() == "UNPROTECTED"
        assert page.locator("#admission-state").inner_text() == "HOLD"
        assert page.locator("#red-body tr").count() == 1
        assert "Verify Black/isort styles" in page.locator("#red-body").inner_text()
        assert page.locator("#run").is_disabled()
        geometry = page.evaluate(
            """() => ({width: window.innerWidth, body: document.body.scrollWidth, doc: document.documentElement.scrollWidth, images:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).length})"""
        )
        assert geometry["body"] <= geometry["width"] + 1, geometry
        assert geometry["doc"] <= geometry["width"] + 1, geometry
        assert geometry["images"] == 0, geometry
        page.screenshot(path=str(ROOT / "qa" / f"{key}.png"), full_page=True)
        qa["viewports"][key] = {
            "width": width,
            "height": height,
            "page_errors": errors,
            "geometry": geometry,
            "status": "PASS" if not errors else "FAIL",
        }
        if key == "desktop":
            page.locator("#red-filter").fill("no-such-step")
            assert (
                "No first-RED matches filter" in page.locator("#red-body").inner_text()
            )
            page.locator("#red-filter").fill("isort")
            assert page.locator("#red-body tr").count() == 1
            page.locator("#load-demo").click()
            page.locator("#analyze-model").click()
            pca = page.locator("#model-result").inner_text()
            assert "DESCRIPTIVE_ONLY" in pca, pca
            assert "eigRank" in pca
            assert page.locator("#pca-chart .model-bar").count() == 3
            qa["model_checks"]["pca_synthetic"] = "PASS_DESCRIPTIVE_ONLY"
            reference = {
                "schema": "code-purple.pca.panel.v1",
                "source_sha": "f" * 40,
                "columns": [{"name": "a", "unit": "s"}, {"name": "b", "unit": "s"}],
                "rows": [
                    {
                        "independent_unit": "r" + str(i),
                        "values": [float(i), float(i * 3 + 2)],
                    }
                    for i in range(40)
                ],
            }
            page.locator("#empirical-input").fill(json.dumps(reference))
            page.locator("#analyze-model").click()
            pca_ref = json.loads(page.locator("#model-result").inner_text())
            assert abs(pca_ref["pc1_variance_pct"] - 100.0) < 1e-8, pca_ref
            assert pca_ref["eigRank"] == 1, pca_ref
            qa["model_checks"]["pca_perfect_correlation_reference"] = "PASS_100PCT_PC1"
            page.locator("#analysis-type").select_option("bt")
            page.locator("#load-demo").click()
            page.locator("#analyze-model").click()
            bt = page.locator("#model-result").inner_text()
            assert "EXPLORATORY_FIT_NO_ACCEPTANCE" in bt, bt
            assert page.locator("#bt-chart .model-bar").count() == 3
            qa["model_checks"]["bt_synthetic"] = "PASS_EXPLORATORY_ONLY"
            balanced = {
                "schema": "code-purple.bt.pairs.v1",
                "source_sha": "f" * 40,
                "items": ["A", "B"],
                "comparisons": [
                    {
                        "winner": "A" if i % 2 else "B",
                        "loser": "B" if i % 2 else "A",
                        "independent_unit": str(i),
                    }
                    for i in range(40)
                ],
            }
            page.locator("#empirical-input").fill(json.dumps(balanced))
            page.locator("#analyze-model").click()
            bt_ref = json.loads(page.locator("#model-result").inner_text())
            assert len(bt_ref["rank"]) == 2, bt_ref
            assert all(
                abs(r["relative_strength"] - 1.0) < 1e-7 for r in bt_ref["rank"]
            ), bt_ref
            qa["model_checks"]["bt_balanced_reference"] = "PASS_EQUAL_STRENGTH"
            row = {
                "schema": "code-purple.bt.pairs.v1",
                "source_sha": "f" * 40,
                "items": ["A", "B"],
                "comparisons": [
                    {"winner": "A", "loser": "B", "independent_unit": str(i)}
                    for i in range(35)
                ],
            }
            page.locator("#empirical-input").fill(json.dumps(row))
            page.locator("#analyze-model").click()
            assert (
                "winning graph not strongly connected"
                in page.locator("#model-result").inner_text()
            )
            qa["model_checks"]["bt_disconnected_rejection"] = "PASS"
            page.locator("#clear-model").click()
            assert "NO MODEL IMPORT" in page.locator("#model-trust").inner_text()
            qa["model_checks"]["clear"] = "PASS"
        page.close()
    browser.close()
server.shutdown()
server.server_close()
(ROOT / "qa" / "browser_qa.json").write_text(json.dumps(qa, indent=2) + "\n")
print(json.dumps(qa, indent=2)[:6500])

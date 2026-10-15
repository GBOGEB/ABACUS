"""Visual and interaction QA for the V3.1 human review dashboard."""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard"
HTML = (OUT / "four_plane_status.html").as_uri()


def run():
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        for name, width, height in (
            ("desktop", 1440, 1000),
            ("laptop", 1280, 800),
            ("mobile", 390, 844),
        ):
            page = browser.new_page(
                viewport={"width": width, "height": height}, device_scale_factor=1
            )
            errors = []
            console = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on(
                "console",
                lambda e: console.append(e.text) if e.type == "error" else None,
            )
            page.set_content(
                (OUT / "four_plane_status.html").read_text(encoding="utf-8"),
                wait_until="load",
            )
            assert page.locator("h1").count() == 1
            assert page.locator("#taskRows tr").count() == 8, "task table missing"
            assert page.locator(".diagram svg").count() == 2
            assert page.locator("#metricTasks").inner_text() == "8"
            page.locator('button[data-plane="diagnostic"]').click()
            assert page.locator("#taskRows tr").count() == 2
            page.locator('button[data-plane="runtime"]').click()
            assert page.locator("#taskRows tr").count() == 1
            page.locator('button[data-plane="all"]').click()
            assert page.locator("#taskRows tr").count() == 8
            page.locator("#importJson").set_input_files(
                {
                    "name": "invalid.json",
                    "mimeType": "application/json",
                    "buffer": b'{"schema":"wrong"}',
                }
            )
            page.wait_for_function(
                "document.querySelector('#importStatus').textContent.includes('Import rejected')",
                timeout=3000,
            )
            assert "HOLD" in page.locator(".pill.hold").inner_text()
            over = page.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth"
            )
            assert not over, f"horizontal overflow {name}"
            assert not errors and not console, (name, errors, console)
            dest = OUT / f"qa-four-planes-{name}.png"
            page.screenshot(path=str(dest), full_page=True)
            checks.append(
                {
                    "viewport": name,
                    "errors": 0,
                    "svg_count": 2,
                    "task_count": 8,
                    "overflow": False,
                    "filter_test": True,
                    "invalid_import_rejected": True,
                    "screenshot": dest.name,
                }
            )
            page.close()
        browser.close()
    return checks


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))

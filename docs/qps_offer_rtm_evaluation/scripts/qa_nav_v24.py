# -*- coding: utf-8 -*-
"""
QA sweep for QPS_RTM_BT_Navigator_v22.html, focused on the new PCA/Structure
tab and the two Lookup-card btLambda additions -- matches this project's own
convention (CONTINUATION.md): "Playwright headless sweep (zero console/page
errors, zero horizontal overflow) for html."
"""
import sys
from playwright.sync_api import sync_playwright

path = sys.argv[1]
url = "file:///" + path.replace("\\", "/")

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.on("console", lambda msg: errors.append(f"CONSOLE {msg.type}: {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(f"PAGEERROR: {exc}"))
    page.goto(url)
    page.wait_for_timeout(500)

    # click the PCA / Structure tab
    tab_btn = page.locator('button[data-tab="pca"]')
    assert tab_btn.count() == 1, "PCA / Structure tab button not found"
    tab_btn.click()
    page.wait_for_timeout(500)

    section = page.locator("#tab-pca")
    assert section.is_visible(), "tab-pca section not visible after click"

    # scatter charts present (2 svg elements: Proposal A + Proposal B)
    svgs = section.locator("svg")
    n_svg = svgs.count()
    print(f"svg count in PCA tab: {n_svg}")
    assert n_svg == 2, f"expected 2 svg scatter charts, found {n_svg}"

    # circle points in Proposal A scatter should be 722
    circles_a = svgs.nth(0).locator("circle")
    print(f"Proposal A circle count: {circles_a.count()}")

    # ascii diagram present
    ascii_pre = section.locator("pre.ascii-diagram")
    assert ascii_pre.count() == 1, "ascii-diagram pre block not found"
    ascii_text = ascii_pre.inner_text()
    assert "BT SCORING" in ascii_text and "PCA (across the population" in ascii_text
    print("ascii diagram present, length:", len(ascii_text))

    # weight scenario 4 table present
    assert "Cost-heavy-proportional" in section.inner_text()

    # horizontal overflow check
    body_w = page.evaluate("document.body.scrollWidth")
    viewport_w = page.evaluate("window.innerWidth")
    print(f"body.scrollWidth={body_w} viewport innerWidth={viewport_w}")
    overflow = body_w > viewport_w + 5

    # click into RTM Lookup, check btLambda field renders
    page.locator('button[data-tab="lookup"]').click()
    page.wait_for_timeout(300)
    inp = page.locator("#lookupInput")
    inp.fill("693")  # numeric-only input (RTM- prefix locked in the UI, see backlog v14 note
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)
    lookup_text = page.locator("#tab-lookup").inner_text()
    assert "BT" in lookup_text and ("index" in lookup_text.lower())
    print("RTM Lookup btLambda field text snippet found")

    browser.close()

print("console/page errors:", len(errors))
for e in errors[:30]:
    print(" ", e)
print("horizontal overflow:", overflow)
if errors or overflow:
    sys.exit(1)
print("QA PASSED")

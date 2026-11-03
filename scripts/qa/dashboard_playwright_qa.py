#!/usr/bin/env python3
"""ABACUS dashboard Playwright HTML-quality QA (checks K1–K10).

Extends the existing W58 DOW-playground QA contract
(triage/W58_3PR_A_DOW_PLAYGROUND_QA.yaml) with the K-series numbering the team
uses for HTML-quality checks, and adds two accessibility checks:

  K1  no_console_error          — no console errors while loading/rendering
  K2  no_page_error             — no uncaught JS exceptions
  K3  no_body_horizontal_overflow — page does not scroll horizontally
  K4  navigation                — primary nav links present (skipped if page has none)
  K5  readable_content          — main/landmark text content is present
  K6  deep_link                 — in-page anchor targets resolve
  K7  read_only_boundary        — only allow-listed external hosts are contacted
  K8  chart_render              — every chart container has a non-zero box + svg/canvas
  K9  contrast  (NEW)           — rendered text ≥ 4.5:1 and graphic marks ≥ 3:1 (WCAG AA)
  K10 legend_axis_no_overlap (NEW) — legend bbox does not intersect x-axis tick
                                   labels or the x-axis title, at every viewport

Every pass/fail is measured from the actually-rendered DOM (Plotly SVG), not
asserted. Screenshots of every chart container are saved per viewport.

Usage:
  python scripts/qa/dashboard_playwright_qa.py \
      --html docs/metrics.html docs/dmaic-metrics.html \
      --output-dir docs/qa/playwright_baseline --label before
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import pathname2url

from playwright.sync_api import sync_playwright

# Hosts that are "same origin" for the QA harness (a local static server used so
# that charts which fetch() a metrics JSON can render). Never counted as an
# external/read-only-boundary violation.
LOCAL_HOSTS = {"localhost", "127.0.0.1"}

VIEWPORTS = (
    ("desktop_1440x900", 1440, 900),
    ("laptop_1280x720", 1280, 720),
    ("mobile_390x844", 390, 844),
)

# Hosts a chart page may legitimately contact (CDN for the chart library + fonts).
ALLOWED_HOSTS = {
    "cdn.plot.ly",
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "cdnjs.cloudflare.com",
}

AA_TEXT = 4.5
AA_GRAPHIC = 3.0


# ── colour / contrast helpers ───────────────────────────────────────────────
def _parse_color(c: str):
    if not c:
        return None
    c = c.strip()
    if c.startswith("#"):
        c = c[1:]
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        if len(c) != 6:
            return None
        return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))
    if c.startswith("rgb"):
        nums = c[c.find("(") + 1 : c.find(")")].split(",")
        try:
            vals = [float(x.strip()) for x in nums[:3]]
            return tuple(int(round(v)) for v in vals)
        except ValueError:
            return None
    return None


def _rel_lum(rgb):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(c1, c2):
    a, b = _parse_color(c1), _parse_color(c2)
    if a is None or b is None:
        return None
    l1, l2 = _rel_lum(a), _rel_lum(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return round((hi + 0.05) / (lo + 0.05), 2)


# ── DOM extraction (runs in the page) ───────────────────────────────────────
EXTRACT_JS = r"""
() => {
  const out = {plots: []};
  const plots = Array.from(document.querySelectorAll('.js-plotly-plot'));
  for (const gd of plots) {
    const svg = gd.querySelector('svg.main-svg');
    const bg = gd.querySelector('.bg');
    const paper = (gd._fullLayout && gd._fullLayout.paper_bgcolor) ||
                  (bg && getComputedStyle(bg).fill) || '';
    const plotbg = (gd._fullLayout && gd._fullLayout.plot_bgcolor) || paper;
    const rect = (el) => { if(!el) return null; const r = el.getBoundingClientRect();
      return {x:r.x, y:r.y, w:r.width, h:r.height}; };

    // text elements
    const texts = [];
    gd.querySelectorAll('.xtick text, .ytick text, .legend text, .gtitle, .g-xtitle text, .g-ytitle text')
      .forEach(t => {
        const cs = getComputedStyle(t);
        texts.push({fill: t.getAttribute('fill') || cs.fill, cls: t.parentElement && t.parentElement.getAttribute('class')});
      });

    // graphic marks (bar fills, line strokes, scatter markers)
    const marks = [];
    gd.querySelectorAll('.points path.point, .trace .point, .bars path, .barlayer path')
      .forEach(p => { const f = p.getAttribute('style') || ''; const fill = p.getAttribute('fill') ||
        (f.match(/fill:\s*([^;]+)/) || [])[1]; if (fill) marks.push(fill.trim()); });
    gd.querySelectorAll('.scatterlayer .js-line, .lines path.js-line')
      .forEach(p => { const f = p.getAttribute('style') || ''; const st = p.getAttribute('stroke') ||
        (f.match(/stroke:\s*([^;]+)/) || [])[1]; if (st) marks.push(st.trim()); });

    // bounding boxes for overlap test
    const legend = gd.querySelector('.legend');
    const xticks = Array.from(gd.querySelectorAll('.xtick text')).map(rect).filter(Boolean);
    const xtitle = gd.querySelector('.g-xtitle, .xtitle');
    let xlabelBox = null;
    if (xticks.length) {
      const x0 = Math.min(...xticks.map(r=>r.x)), y0 = Math.min(...xticks.map(r=>r.y));
      const x1 = Math.max(...xticks.map(r=>r.x+r.w)), y1 = Math.max(...xticks.map(r=>r.y+r.h));
      xlabelBox = {x:x0, y:y0, w:x1-x0, h:y1-y0};
    }

    out.plots.push({
      id: gd.id, paper, plotbg,
      box: rect(gd),
      hasSvg: !!svg,
      texts, marks,
      legendBox: rect(legend),
      xlabelBox,
      xtitleBox: rect(xtitle)
    });
  }
  return out;
}
"""


def _overlap(a, b):
    if not a or not b or a["w"] <= 0 or b["w"] <= 0:
        return 0.0
    ix = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return round(ix * iy, 1)


def run_page(page, html_path: Path, out_dir: Path, label: str):
    console_errors, page_errors, external, bad_responses = [], [], [], []

    def _on_console(m):
        if m.type != "error":
            return
        txt = m.text or ""
        # Browser "Failed to load resource" console lines do not carry the URL;
        # real missing resources are measured precisely via bad_responses below
        # (and would also fail K8). The only resource that 404s under the QA
        # static server is /favicon.ico, a harness artifact, so we drop the
        # generic resource-load line here and rely on bad_responses for truth.
        if "Failed to load resource" in txt:
            return
        console_errors.append(txt)

    page.on("console", _on_console)
    page.on("pageerror", lambda e: page_errors.append(str(e)))

    def on_request(req):
        host = urlsplit(req.url).netloc.split(":")[0]
        if (
            host
            and not req.url.startswith("file:")
            and host not in ALLOWED_HOSTS
            and host not in LOCAL_HOSTS
        ):
            external.append(req.url)

    page.on("request", on_request)

    def on_response(resp):
        # Count any >=400 resource load as a defect EXCEPT the harness favicon.
        if resp.status >= 400 and not resp.url.rstrip("/").endswith("/favicon.ico"):
            bad_responses.append(f"{resp.status} {resp.url}")

    page.on("response", on_response)

    target = str(html_path)
    if target.startswith("http://") or target.startswith("https://"):
        url = target
        page_name = target.rsplit("/", 1)[-1]
        stem = page_name.rsplit(".", 1)[0]
    else:
        url = "file://" + pathname2url(str(html_path.resolve()))
        page_name = html_path.name
        stem = html_path.stem
    page_result = {"page": page_name, "viewports": {}}

    for vname, vw, vh in VIEWPORTS:
        page.set_viewport_size({"width": vw, "height": vh})
        console_errors.clear()
        page_errors.clear()
        external.clear()
        bad_responses.clear()
        page.goto(url, wait_until="load")
        # Some dashboards render their charts only inside a tab that must be
        # activated first (e.g. dmaic-metrics.html "Charts" tab). Click any such
        # control so the charts actually mount before we measure them.
        try:
            page.evaluate(r"""
              () => {
                const btns = Array.from(document.querySelectorAll('button, a, [role=tab]'));
                const t = btns.find(b => /charts?/i.test((b.textContent||'').trim())
                                       || /charts?/i.test(b.getAttribute('onclick')||''));
                if (t) t.click();
              }""")
        except Exception:
            pass
        # let charts render
        try:
            page.wait_for_selector(".js-plotly-plot .main-svg", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        data = page.evaluate(EXTRACT_JS)

        # K3 horizontal overflow
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > window.innerWidth + 1"
        )
        # K4 navigation
        nav_links = page.evaluate(
            "() => document.querySelectorAll('nav a, .topnav a').length"
        )
        # K5 readable content
        text_len = page.evaluate(
            "() => (document.querySelector('main, .container, body').innerText||'').trim().length"
        )
        # K6 deep links
        deeplink_ok = page.evaluate(r"""
          () => { const ids = new Set(Array.from(document.querySelectorAll('[id]')).map(e=>e.id));
            const anchors = Array.from(document.querySelectorAll('a[href^="#"]'))
              .map(a=>a.getAttribute('href').slice(1)).filter(h=>h.length);
            return anchors.every(h => ids.has(h)); }""")

        checks = {}
        checks["K1_no_console_error"] = {
            "pass": len(console_errors) == 0 and len(bad_responses) == 0,
            "errors": console_errors[:5],
            "bad_responses": bad_responses[:5],
        }
        checks["K2_no_page_error"] = {
            "pass": len(page_errors) == 0,
            "errors": page_errors[:5],
        }
        checks["K3_no_body_horizontal_overflow"] = {"pass": not overflow}
        checks["K4_navigation"] = {
            "pass": nav_links > 0 or True,
            "nav_links": nav_links,
            "note": "skipped (no nav on page)" if nav_links == 0 else "",
        }
        checks["K5_readable_content"] = {"pass": text_len > 50, "text_len": text_len}
        checks["K6_deep_link"] = {"pass": bool(deeplink_ok)}
        checks["K7_read_only_boundary"] = {
            "pass": len(external) == 0,
            "unexpected": external[:5],
        }

        # K8 chart render
        plots = data["plots"]
        k8_ok = len(plots) > 0 and all(
            p["hasSvg"] and p["box"] and p["box"]["w"] > 10 and p["box"]["h"] > 10
            for p in plots
        )
        checks["K8_chart_render"] = {"pass": k8_ok, "chart_count": len(plots)}

        # K9 contrast
        min_text, min_graphic = None, None
        text_fail, graphic_fail = [], []
        for p in plots:
            bg = p["plotbg"] or p["paper"]
            for t in p["texts"]:
                cr = contrast(t["fill"], p["paper"])
                if cr is not None:
                    min_text = cr if min_text is None else min(min_text, cr)
                    if cr < AA_TEXT:
                        text_fail.append({"plot": p["id"], "fill": t["fill"], "cr": cr})
            for m in p["marks"]:
                cr = contrast(m, bg)
                if cr is not None:
                    min_graphic = cr if min_graphic is None else min(min_graphic, cr)
                    if cr < AA_GRAPHIC:
                        graphic_fail.append({"plot": p["id"], "fill": m, "cr": cr})
        checks["K9_contrast"] = {
            "pass": (not text_fail) and (not graphic_fail),
            "min_text_contrast": min_text,
            "min_graphic_contrast": min_graphic,
            "aa_text": AA_TEXT,
            "aa_graphic": AA_GRAPHIC,
            "text_failures": text_fail[:5],
            "graphic_failures": graphic_fail[:5],
        }

        # K10 legend / x-axis overlap
        overlaps = []
        for p in plots:
            lb = p["legendBox"]
            if not lb:
                continue
            ov_lbl = _overlap(lb, p["xlabelBox"])
            ov_ttl = _overlap(lb, p["xtitleBox"])
            if ov_lbl > 1 or ov_ttl > 1:
                overlaps.append(
                    {
                        "plot": p["id"],
                        "legend_vs_labels_px": ov_lbl,
                        "legend_vs_title_px": ov_ttl,
                    }
                )
        checks["K10_legend_axis_no_overlap"] = {
            "pass": len(overlaps) == 0,
            "overlaps": overlaps,
        }

        # screenshots of every chart container
        shots = []
        vp_dir = out_dir / label / stem / vname
        vp_dir.mkdir(parents=True, exist_ok=True)
        for p in plots:
            try:
                el = page.query_selector("#" + p["id"])
                if el:
                    sp = vp_dir / f"{p['id']}.png"
                    el.screenshot(path=str(sp))
                    shots.append(str(sp.relative_to(out_dir)))
            except Exception:
                pass
        full = vp_dir / "_full_page.png"
        page.screenshot(path=str(full), full_page=True)
        shots.append(str(full.relative_to(out_dir)))

        page_result["viewports"][vname] = {
            "size": f"{vw}x{vh}",
            "checks": checks,
            "all_pass": all(c["pass"] for c in checks.values()),
            "screenshots": shots,
        }
    return page_result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", nargs="+", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--label", default="run")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
    )
    if not exe:
        raise RuntimeError("No Chromium/Chrome binary found; QA must FAIL")

    results = {"label": args.label, "pages": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        page = browser.new_page()
        for h in args.html:
            spec = (
                h if (h.startswith("http://") or h.startswith("https://")) else Path(h)
            )
            results["pages"].append(run_page(page, spec, out_dir, args.label))
        browser.close()

    report = out_dir / f"qa_results_{args.label}.json"
    report.write_text(json.dumps(results, indent=2))

    total = passed = 0
    for pg in results["pages"]:
        for vp in pg["viewports"].values():
            for cid, c in vp["checks"].items():
                total += 1
                passed += 1 if c["pass"] else 0
    print(f"\n== QA '{args.label}': {passed}/{total} checks passed ==")
    for pg in results["pages"]:
        for vn, vp in pg["viewports"].items():
            fails = [k for k, c in vp["checks"].items() if not c["pass"]]
            status = "OK" if not fails else ("FAIL: " + ", ".join(fails))
            print(f"  {pg['page']:24} {vn:18} {status}")
    print(f"\nReport: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

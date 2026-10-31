#!/usr/bin/env python3
"""
render_all.py — Generate slides.html (and per-slide HTML) from master/slides.md.

Usage:
    python3 master/render_all.py            # writes slides.html + slides/<id>.html
    python3 master/render_all.py --watch    # (optional) re-render on change

Inputs:
    master/slides.md   — canonical markdown with `---` slide separators + front-matter
    master/config.yaml — theme/fonts/layouts
    master/data.json   — structured data
    master/truth.md    — SSoT (rendered into truth.html separately)

Outputs:
    slides.html              — combined deck
    slides/<id>.html         — individual slide pages (used by slide-editor.html)
"""
from __future__ import annotations
import json, os, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "master"
OUT_SLIDES = ROOT / "slides.html"
OUT_DIR = ROOT / "slides"
OUT_DIR.mkdir(exist_ok=True)

# ---------- minimal YAML loader (front-matter subset) ----------
def parse_frontmatter(block: str) -> dict:
    out, key, buf = {}, None, []
    for line in block.splitlines():
        m = re.match(r'^([a-zA-Z_][\w-]*):\s*(.*)$', line)
        if m and not line.startswith(' '):
            if key is not None:
                out[key] = "\n".join(buf).rstrip()
            key, val = m.group(1), m.group(2)
            if val == "|":
                buf = []
            else:
                out[key] = val
                key, buf = None, []
        elif key is not None:
            buf.append(line[2:] if line.startswith("  ") else line)
    if key is not None:
        out[key] = "\n".join(buf).rstrip()
    return out

# ---------- minimal markdown → HTML ----------
def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            code = []
            while j < len(lines) and not lines[j].startswith("```"):
                code.append(lines[j]); j += 1
            out.append('<pre class="ascii"><code>' + html.escape("\n".join(code)) + "</code></pre>")
            i = j + 1; continue
        if re.match(r'^#{1,6} ', ln):
            n = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{n}>{inline(ln[n+1:])}</h{n}>")
            i += 1; continue
        if re.match(r'^\s*[-*] ', ln):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*] ', lines[i]):
                items.append(f"<li>{inline(lines[i].lstrip()[2:])}</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        if re.match(r'^\s*\d+\. ', ln):
            items = []
            while i < len(lines) and re.match(r'^\s*\d+\. ', lines[i]):
                stripped = re.sub(r'^\s*\d+\. ', '', lines[i])
                items.append(f"<li>{inline(stripped)}</li>"); i += 1
            out.append("<ol>" + "".join(items) + "</ol>"); continue
        if ln.strip() == "":
            i += 1; continue
        # paragraph
        para = [ln]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,6} |```|\s*[-*] |\s*\d+\. )', lines[i]):
            para.append(lines[i]); i += 1
        out.append("<p>" + inline(" ".join(para)) + "</p>")
    return "\n".join(out)

def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    return s

# ---------- slide parsing ----------
def parse_slides(md_text: str) -> list[dict]:
    blocks = re.split(r'(?m)^---\s*$', md_text)
    slides = []
    # blocks alternate: [preamble, fm1, body1, fm2, body2, ...]
    # we treat any block starting with `id:` (after stripping) as front-matter
    i = 0
    while i < len(blocks):
        b = blocks[i].strip()
        if b.startswith("id:") or re.match(r'^[a-z_]+:\s', b):
            fm = parse_frontmatter(b)
            body = blocks[i+1] if i+1 < len(blocks) else ""
            fm["body"] = body.strip()
            slides.append(fm); i += 2
        else:
            i += 1
    return slides

# ---------- HTML rendering ----------
def load_config():
    txt = (MASTER / "config.yaml").read_text()
    # ultra-minimal: just pull theme colors + fonts via regex
    def grab(key, default=""):
        m = re.search(rf'{key}:\s*"?([^"\n]+)"?', txt)
        return m.group(1).strip() if m else default
    return {
        "primary": grab("primary", "#0b3d91"),
        "accent":  grab("accent", "#ff8a00"),
        "bg":      grab("bg", "#f7f8fa"),
        "fg":      grab("fg", "#1b1f24"),
        "rule":    grab("rule", "#d8dde3"),
        "body_font": "Aptos, 'Segoe UI', system-ui, Helvetica, Arial, sans-serif",
        "mono_font": "Consolas, 'JetBrains Mono', 'Courier New', monospace",
    }

CSS_TEMPLATE = """
:root {{
  --primary:{primary}; --accent:{accent}; --bg:{bg}; --fg:{fg}; --rule:{rule};
  --body:{body_font}; --mono:{mono_font};
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:var(--body); color:var(--fg); background:var(--bg); }}
.deck {{ max-width:1100px; margin:0 auto; padding:24px; }}
.slide {{ background:#fff; border:1px solid var(--rule); border-radius:12px;
  padding:32px 40px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
.slide h1 {{ color:var(--primary); margin-top:0; }}
.slide .sub {{ color:#5b6470; margin-top:-6px; margin-bottom:18px; }}
.slide .label {{ display:inline-block; font-family:var(--mono); font-size:12px;
  background:var(--primary); color:#fff; padding:2px 8px; border-radius:6px; margin-right:8px; }}
.ascii, pre, code {{ font-family:var(--mono); }}
pre.ascii {{ background:#0e1116; color:#e6edf3; padding:16px; border-radius:8px;
  overflow:auto; line-height:1.45; }}
.caption {{ font-size:13px; color:#5b6470; font-style:italic; margin-top:6px; }}
.notes {{ margin-top:18px; border-top:1px dashed var(--rule); padding-top:10px;
  font-size:13px; color:#5b6470; }}
.notes b {{ color:var(--accent); }}
.layout-text-table, .layout-text-graph {{ display:grid; grid-template-columns:1.618fr 1fr; gap:24px; }}
.layout-4-quadrants {{ display:grid; grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr; gap:16px; }}
"""

def render_slide(s: dict, idx: int, total: int) -> str:
    layout = s.get("layout", "text-only")
    title = html.escape(s.get("title", ""))
    sub = html.escape(s.get("subtitle", ""))
    cap = html.escape(s.get("caption", ""))
    notes = s.get("notes", "")
    body_html = md_to_html(s.get("body", ""))
    sid = s.get("id", f"slide-{idx}")
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    cap_html = f'<div class="caption">{cap}</div>' if cap else ""
    notes_html = ""
    if notes.strip():
        decorated = re.sub(r'\b(TODO|REVIEW|ACTION)\b', r'<b>\1</b>', html.escape(notes))
        notes_html = f'<div class="notes"><b>Slide notes</b><br>{decorated.replace(chr(10), "<br>")}</div>'
    return f"""
<section class="slide layout-{layout}" id="{sid}" data-index="{idx}">
  <div><span class="label">{idx+1}/{total}</span><span class="label">{layout}</span></div>
  <h1>{title}</h1>
  {sub_html}
  <div class="content">{body_html}</div>
  {cap_html}
  {notes_html}
</section>"""

def render_deck(slides: list[dict], cfg: dict) -> str:
    css = CSS_TEMPLATE.format(**cfg)
    body = "\n".join(render_slide(s, i, len(slides)) for i, s in enumerate(slides))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>MYRRHA QPLANT — Slides (master-rendered)</title>
<style>{css}</style></head>
<body><div class="deck">
<header style="margin-bottom:16px"><a href="index.html">← Hub</a> ·
<a href="slide-editor.html">Open Slide Editor</a> ·
<small>Rendered from <code>master/slides.md</code></small></header>
{body}
</div></body></html>"""

def main():
    cfg = load_config()
    slides = parse_slides((MASTER / "slides.md").read_text())
    OUT_SLIDES.write_text(render_deck(slides, cfg))
    # per-slide HTML for editor preview
    for i, s in enumerate(slides):
        css = CSS_TEMPLATE.format(**cfg)
        page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}
body{{padding:0}}.deck{{padding:0;margin:0}}</style></head><body><div class="deck">
{render_slide(s, i, len(slides))}</div></body></html>"""
        (OUT_DIR / f"{s.get('id', f'slide-{i}')}.html").write_text(page)
    # write slides.json index for editor
    idx = [{"id": s.get("id", f"slide-{i}"),
            "title": s.get("title", ""),
            "subtitle": s.get("subtitle", ""),
            "layout": s.get("layout", "text-only"),
            "caption": s.get("caption", ""),
            "notes": s.get("notes", ""),
            "body": s.get("body", "")} for i, s in enumerate(slides)]
    (ROOT / "slides.json").write_text(json.dumps(idx, indent=2))
    print(f"Rendered {len(slides)} slides → slides.html + slides/*.html + slides.json")

if __name__ == "__main__":
    main()

# MYRRHA Handover — Editing Guide

## 1. Where content lives
| File                    | Role                                       |
|-------------------------|--------------------------------------------|
| `master/slides.md`      | **MASTER** — every slide (markdown)        |
| `master/truth.md`       | SSoT narrative (B1..B5)                    |
| `master/config.yaml`    | Theme, fonts, layouts, slide order         |
| `master/data.json`      | All numeric data (single edit point)       |
| `master/render_all.py`  | Generator → `slides.html`, `slides/*.html`, `slides.json` |

## 2. Master markdown syntax
Slides are separated by `---` and start with YAML-ish front-matter:

```
---
id: hierarchy
title: MYRRHA QPLANT System Hierarchy
subtitle: Canonical decomposition
layout: text-only
caption: F1 — System decomposition tree
notes: |
  TODO: validate skid IDs.
  REVIEW: cross-check with Kaeser nameplates.
---
# Body in markdown
- bullets, **bold**, *italic*, `code`
```ascii
QPLANT
└── ...
```
```

Supported body markdown: `# .. ######` headings, `-`/`*` bullets, ordered lists,
fenced code (rendered in Consolas), `**bold**`, `*italic*`, `` `code` ``.

## 3. Adding / removing slides
1. Edit `master/slides.md` (insert a new `---` block).
2. Optional: add the slide id to `slides_order` in `master/config.yaml`.
3. Run `python3 master/render_all.py`.

## 4. Updating data tables
Edit `master/data.json` (or use **truth.html → Edit mode** which downloads a
fresh `data.json` with a change-log entry). Then re-run the renderer.

## 5. Live editing per slide
Open `slide-editor.html`. The left pane shows the rendered slide; the right pane
edits title / subtitle / layout / body / caption / notes. Changes auto-preview
and are persisted to `localStorage` on **Save**. Use **Export slide HTML/Markdown**
to round-trip back into `master/slides.md`.

## 6. Regenerating outputs
```bash
cd /home/ubuntu/myrrha_handover
python3 master/render_all.py
```
Outputs:
- `slides.html` — combined deck
- `slides/<id>.html` — per-slide pages
- `slides.json` — index consumed by `slide-editor.html`

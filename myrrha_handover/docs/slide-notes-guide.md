# MYRRHA Handover — Slide Notes Guide

Slide notes are free-form review/action commentary attached to each slide.
They render under a dashed divider, in muted text, with keyword highlighting.

## Comment syntax
Use plain prose. The renderer highlights three keywords in accent orange:

| Keyword  | Meaning                                       |
|----------|-----------------------------------------------|
| `TODO`   | Work item — must be completed before sign-off |
| `REVIEW` | Needs validation by another engineer          |
| `ACTION` | Concrete action point with an owner           |

Example:
```
TODO: confirm B2 against latest test bench data.
REVIEW: K. (Kaeser) to verify HP3 nameplate.
ACTION: schedule v0.5 meeting before 2026-06-01.
```

## Where to write notes
- **Master:** in `master/slides.md` under the `notes: |` front-matter key.
  All lines must be indented two spaces under the `|`.
- **Editor:** `slide-editor.html` → bottom textarea (yellow background).
  Saves to `localStorage`; export with **Export slide Markdown** and paste back
  into `master/slides.md` to make the change canonical.

## Conventions
- One bullet per discrete action.
- Prefix with date (`2026-05-10 — TODO: …`) if status matters.
- Keep notes off the printed/exported slide by removing the `notes:` block before
  publishing if needed (the renderer hides notes only when the field is empty).

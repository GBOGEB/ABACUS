# SSOT Style Pipeline

This control surface defines how ABACUS should evaluate generated and final rendered
artifacts without committing binary outputs to GitHub. The source of truth is
`ssot/ssot_style.json`; `scripts/validate_ssot_style.py` validates the contract,
scores which local graph, DOW, KEB, HTML and Playwright nodes are currently awake,
and separates path presence from evidence depth.

## Repo Roles

| Repo | Role | Current signal |
| --- | --- | --- |
| `GBOGEB/ABACUS` | User-facing dashboards, HTML navigators, runtime evidence, DOW/KEB tests and artifact QA. | Broadest artifact estate; style/readability QA was scattered. |
| `GBOGEB/CODEX` | Schemas, validators, render governance, federation and reusable CI patterns. | Strong render and contrast test inventory. |
| Controlled evidence repo | Non-public QPS evidence, canonical records, release packs and cost roundtrip. | Compact Playwright and release-pack pattern. |

## Artifact Contract

| Artifact | Required QA evidence |
| --- | --- |
| Excel | ZIP/XML integrity, formula scan, controlled totals, scenario labels, recalculation/open-save evidence. |
| PPTX | YAML/content binding, theme binding, rendered slide count, overlap/out-of-bounds scan, notes/sources, slide reference. |
| PDF | Every page rendered, no blank pages, clipping/glyph scan, page reference. |
| HTML | Playwright navigation, no console errors, no horizontal overflow, links resolve, visible SSOT hash, stale banner when needed. |
| Markdown | Changed-docs lint, crosswalk links, visible evidence class. |
| Graphs | Source-data binding, nonzero nodes/edges, runtime status, stale/dormant node flagging. |

## DMAIC Loop

| Phase | Control question | Current direction |
| --- | --- | --- |
| Define | What is the style/readability/rendering SSOT? | `ssot_style.json`. |
| Measure | Which artifact and graph nodes are actually present? | `validate_ssot_style.py` awake score. |
| Analyze | Which underdeveloped axes explain the most risk? | PCA axes: style authority, render evidence, artifact linkage, graph awake state, CI control. |
| Improve | Which narrow change wakes the most evidence? | Add tests and manifest before wiring more CI fan-out. |
| Control | How does this stay governed? | Standard-library validator, report JSON option, CI-ready command. |

## BT Priority

The next improvement should rank by:

1. Prevent stale outward artifacts from looking current.
2. Wake dormant graph/runtime evidence nodes.
3. Add Playwright coverage where HTML is a review or scenario interface.
4. Consolidate style palettes before changing colors manually.
5. Keep heavy PPTX/PDF/XLSX rendering in full/manual or scheduled tiers.

## Node Penetration

The validator reports two related numbers:

| Metric | Meaning |
| --- | --- |
| `awake_score` | Weighted probe paths exist in the repo. This answers whether the node is present. |
| `penetration_score` | Probe contents show deeper evidence: graph topology, dependencies, objectives, Playwright browser/layout checks, DOW agent status, KEB runtime/tests, or visible PCA/BT HTML. |

An awake score can be high while penetration is still incomplete. That is expected:
presence is the first gate; rendered evidence, stale banners, screenshots, hashes and
roundtrip logs are the next wave.

## Commands

```bash
python scripts/validate_ssot_style.py --output reports/ssot_style_status.json
python -m unittest tests.test_validate_ssot_style -v
```

# W009 — Final Deliverables & Commissioning

**Status:** active (infrastructure landed; awaiting engineering sign-off)
**Wave goal:** turn the W006 heuristic cross-map + W008 reviewer triage into a
**commissioned v1.0 canonical register** with a formal engineering **sign-off
record**, without ever fabricating an engineering confirmation.

---

## 1. Why W009 exists

W005 proved the design register (circuit-sequential, e.g. `CV001`) and the
as-drawn catalog (instance-numbered, e.g. `CV560`) use **orthogonal** tag
schemes → exact tag overlap is **0%**. W006 produced a confidence-scored
heuristic cross-map (43 pairs: 39 MEDIUM, 4 LOW; 54 unmapped) but, by design,
**0 HIGH** pairs — HIGH requires an independent corroborator or a human-confirmed
seed. W008 gave reviewers an interactive surface to triage those pairs.

W009 closes the loop: it ingests reviewer decisions, promotes confirmed pairs to
HIGH, and publishes the commissioned register + sign-off record.

## 2. The honesty invariant (do not break)

- `configs/known_seeds.json` is **committed empty**. Seeds are added **only** by
  ingesting reviewer-confirmed viewer decisions — never hand-written, never
  inferred.
- A tag is `commissioned` **only** when backed by a HIGH-tier score (≥0.80),
  which means an engineering-confirmed seed (score 1.0) or independent signal
  corroboration.
- With no confirmed seeds the honest baseline is **0 commissioned / 43
  provisional / 54 open**. The release artifacts say exactly that.

## 3. Commissioning status

| Status | Meaning | Source |
| --- | --- | --- |
| `commissioned` | trustworthy design↔as-drawn identity | HIGH tier or confirmed seed |
| `provisional` | plausible but unconfirmed | MEDIUM / LOW heuristic pair |
| `open` | no candidate found | unmapped design tag |

## 4. The commissioning workflow

```
┌─ output/interactive_viewer.html ─┐   reviewer triages pairs (Confirm/Reject/Defer)
│  ⬇ Triage  →  triage_decisions.json │
└──────────────┬───────────────────┘
               │  python3 -m abacus_svg_pid.ingest_triage triage_decisions.json
               ▼
        configs/known_seeds.json   (reviewer-CONFIRMED seeds + provenance/audit)
               │  python3 -m abacus_svg_pid.build_w006_crossmap   (applies seeds → HIGH)
               ▼
        data/crossmap/crossmap_confidence.json
               │  python3 -m abacus_svg_pid.build_w009_release
               ▼
   data/excel/canonical_register_release_v1.0.yaml   (commissioned register)
   reports/W009_SIGNOFF_RECORD.{json,md}             (sign-off sheet)
   reports/W009_COMMISSIONING_REPORT.md              (release summary)
```

### Step-by-step

1. **Triage** — open `output/interactive_viewer.html`, review each pair, click
   Confirm / Reject / Defer. Decisions persist in `localStorage`.
2. **Export** — click **⬇ Triage** to download `triage_decisions.json`.
3. **Ingest** —
   ```bash
   PYTHONPATH=src python3 -m abacus_svg_pid.ingest_triage triage_decisions.json
   # add --dry-run first to preview what will be accepted/dropped
   ```
   Each confirmed pair is validated: both tags must exist in the W005 registers
   and their ISA TYPE prefixes must match. Rejected/deferred counts are recorded
   in the `audit` block. Dropped pairs print a `[warn]` line.
4. **Apply** — re-run the cross-map so seeds score 1.0 → HIGH:
   ```bash
   PYTHONPATH=src python3 -m abacus_svg_pid.build_w006_crossmap
   ```
5. **Release** — regenerate the commissioned register + sign-off record:
   ```bash
   PYTHONPATH=src python3 -m abacus_svg_pid.build_w009_release
   ```
6. **Sign off** — complete `reports/W009_SIGNOFF_RECORD.md` (reviewer name,
   role, date, decision) and mirror the values into
   `reports/W009_SIGNOFF_RECORD.json`, then commit.

Steps 3–5 are also wired into `./make.sh` (step 7) for a full regeneration; the
ingest step (3) is manual because it consumes a reviewer-produced file.

## 5. Deliverables

| Artifact | Description | Tracked |
| --- | --- | --- |
| `configs/known_seeds.json` | reviewer-confirmed seeds (KNOWN_SEEDS source) | yes |
| `data/excel/canonical_register_release_v1.0.yaml` | commissioned v1.0 register | derived (regenerate) |
| `reports/W009_commissioning_statistics.json` | stable counts for the CI golden-gate | yes |
| `reports/W009_SIGNOFF_RECORD.{json,md}` | engineering sign-off record | yes (md), derived (json) |
| `reports/W009_COMMISSIONING_REPORT.md` | release summary | yes |

## 6. Tests & CI

- `tests/test_w009_commissioning.py` — 13 tests covering seed extraction,
  validation (TYPE-gate, register existence), provenance/audit, the seed-loader's
  graceful degradation, register assembly, the HIGH→commissioned mapping, and the
  honesty invariant (committed `known_seeds.json` must be empty).
- `ci/golden_gate.py` provides a statistics drift gate for `reports/W009_commissioning_statistics.json`; ensure the CI workflow calls it to enforce semantic stability.

## 7. Definition of done (engineering sign-off)

- [ ] All 43 provisional pairs triaged (confirm / reject) in the viewer.
- [ ] The 54 open tags investigated (mapped where a candidate exists, or
      annotated as genuinely absent from the as-drawn set).
- [ ] `triage_decisions.json` ingested; `configs/known_seeds.json` populated.
- [ ] `build_w006_crossmap` + `build_w009_release` re-run; counts reviewed.
- [ ] `reports/W009_SIGNOFF_RECORD.md` completed and committed.

---
_See also: `docs/W006_INTERACTIVE_UI_PLAN.md`, `docs/W007_MANUAL_SETUP.md`,
`reports/W009_COMMISSIONING_REPORT.md`._

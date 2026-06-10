# DeepAgent Handover Package — Roadmap

**Last updated**: June 7, 2026
**Current release**: **v2.0.0** (handover package merged via PR #383; build/metadata hardened via PR #558)
**Owner**: [GBOGEB](https://github.com/GBOGEB)

This roadmap schedules the follow-up work identified in `REMAINING_TODO_CHECKLIST.md` and the "Future Versions" plan in `README.md`. Dates are **target windows**, not commitments, and assume a part-time maintenance cadence.

---

## Milestone Overview

| Version | Theme | Target Window | Status |
|---------|-------|---------------|:------:|
| **v2.0.0** | Handover package + build/metadata hardening | ✅ Jun 2026 | **Released** |
| **v2.1.0** | Test suite & quality gates | Q3 2026 (Jul–Sep) | 📋 Planned |
| **v2.2.0** | Merged QSYS master presentation | Q3 2026 (Aug–Sep) | 📋 Planned |
| **v2.3.0** | Web dashboard (framework management) | Q4 2026 (Oct–Dec) | 📋 Planned |
| **v3.0.0** | External integrations & plugin ecosystem | Q1 2027 (Jan–Mar) | 📋 Planned |

---

## v2.0.0 — Foundation (Released ✅, June 2026)

**Delivered:**
- Complete handover package (44 artifacts) merged to `main` (PR #383).
- TypeScript framework with working build (`npm run build` → `dist/`), declarations & source maps.
- MIT `LICENSE`, finalized ownership/contact metadata.
- Post-merge verification report, remaining-TODO checklist, security triage report.

---

## v2.1.0 — Test Suite & Quality Gates (Target: Q3 2026)

**Goal:** Establish automated confidence in the TypeScript framework.

| Item | Description | Dependencies |
|------|-------------|--------------|
| Unit test framework | Add Jest (or Vitest) + `ts-jest`; wire `npm test`. | v2.0 build config ✅ |
| Core module tests | Cover `framework`, `kpi`, `dmaic`, `automation`, `handover` (target ≥ 70% line coverage). | Test framework |
| Example projects | 1–2 runnable end-to-end samples under `examples/`. | Core tests |
| CI integration | GitHub Actions job: `npm ci && npm run build && npm test` on PRs. | Test framework |
| Coverage reporting | Upload coverage (Codecov action already present in repo). | CI integration |

**Exit criteria:** green CI on PRs; `npm test` runs a real suite (replaces the v2.0 placeholder).

---

## v2.2.0 — Merged QSYS Master Presentation (Target: Q3 2026)

**Goal:** Execute the 6 next-steps from `analysis/QSYS_Analysis_Executive_Summary.md`.

| Item | Description | Dependencies |
|------|-------------|--------------|
| Deduplicate sources | Use primary `.pptx` over `_fontnorm` copies. | `qsys_slide_dump.json` ✅ |
| Master slide template | ROOT-compliant template. | Dedupe |
| Hierarchical assembly | Organize 389 slides into the recommended structure. | Master template |
| Preserve visuals | Retain images/diagrams with consistent formatting. | Assembly |
| Navigation & cross-refs | Section nav aids + cross-references. | Assembly |
| Appendices | Detailed technical-spec appendices. | Assembly |

**Exit criteria:** single ROOT-compliant merged QSYS deck checked into `source/` or `analysis/`.

---

## v2.3.0 — Web Dashboard (Target: Q4 2026)

**Goal:** Visual management surface for framework KPIs, DMAIC phases, and handover status.

| Item | Description | Dependencies |
|------|-------------|--------------|
| Dashboard scaffold | Lightweight web app (e.g. React/Vite) consuming the compiled `dist/` library. | v2.1 build/tests |
| KPI views | Render `KPIManager` reports/thresholds. | `kpi` module |
| DMAIC tracker | Visualize phase transitions & deliverables. | `dmaic` module |
| Handover board | Status of recursive handover sections. | `handover` module |
| Deploy | GitHub Pages (deploy-pages action already present). | Dashboard scaffold |

**Exit criteria:** deployable dashboard reading live framework data.

---

## v3.0.0 — Integrations & Plugin Ecosystem (Target: Q1 2027)

**Goal:** Connect the framework to external tooling and allow extension.

| Item | Description | Dependencies |
|------|-------------|--------------|
| Plugin API | Stable extension points + interface contracts. | v2.x APIs stable |
| GitHub integration | Sync handover/KPI state with issues/PRs. | Plugin API |
| Jira integration | Map DMAIC deliverables to Jira issues. | Plugin API |
| Slack integration | KPI threshold / phase-transition notifications. | Plugin API |
| ML-based insights | Optional analytics on KPI trends. | Dashboard (v2.3) |

**Exit criteria:** at least one external integration shipped behind the plugin API.

---

## Continuous / Cross-Cutting Workstreams

| Workstream | Cadence | Notes |
|------------|---------|-------|
| **Security** | Ongoing | Apply `SECURITY_TRIAGE_REPORT.md` fixes (`setuptools>=78.1.1`, `jinja2>=3.1.6`); enable Dependabot auto-updates. |
| **Docs** | Per release | Keep `README.md`, implementation README, and `MANIFEST.yaml` in sync with shipped scripts. |
| **Dependency hygiene** | Monthly | `npm update` / pip constraint review. |

---

## Dependency Graph (high level)

```
v2.0 (build/metadata) ──► v2.1 (tests/CI) ──► v2.3 (dashboard) ──► v3.0 (integrations)
                      └──► v2.2 (QSYS deck) ─────────────────────┘
Security & Docs: continuous, parallel to all milestones.
```

---

*Maintained by [GBOGEB](https://github.com/GBOGEB). Proposed dates may shift with capacity; see `REMAINING_TODO_CHECKLIST.md` for the granular backlog.*

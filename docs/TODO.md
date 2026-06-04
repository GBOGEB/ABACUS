# TODO — Outstanding & Deferred Work

Tracked against the wave roadmap (`configs/wave_registry.json`). Items below are the
honest backlog after the v6.0 (W003+W004) build.

---

## High priority (data fidelity)

- [ ] **Recover the U line** (top-left). Currently rendered black; needs colour
  re-attribution so it joins the parent-header tree alongside A/B/D/E/W/S/V.
- [ ] **Map the 112 residual `UNRESOLVED_OTHER_COLOUR` elements** (magenta / non-canonical
  family). Requires augmenting the legend swatch table or a manual engineering call.
- [ ] **Bind the 77 floating arrows** to their source lines (nearest-line / direction
  heuristic) so flow topology is complete.

## Medium priority (layer completeness)

- [ ] Populate **04G_E_RED** line-geometry layer (RED is currently text-only).
- [ ] Populate **03A_Manifold_COLD_Header** and **03B_Manifold_WARM_Header** layers.
- [ ] Verify handover-diamond category prefix per **AD_01.16** (continuity flag #2).
- [ ] Visual review of the **W-line bottom-right zone** (19 elements, atlas layer 04C).

## Future waves (planned, not started)

- [ ] **W005** — Tag & Instrument Association (geometric proximity / CTM validation).
- [ ] **W006** — Cross-drawing reconciliation (unify QCELL ↔ RFCELL line identity).
- [ ] **W007** — Temperature / pressure annotation per segment (4.5 K / 2 K / warm).
- [ ] **W008** — Round-trip reassembly (recompose isolated lines into full P&ID).
- [ ] **W009** — Publication & engineering sign-off.

## Engineering / infra (deferred)

- [ ] CI / GitHub Actions workflow (planned in `docs/GITHUB_PR_PLAN.md`).
- [ ] Web UI / interactive app beyond the current static HTML atlas.
- [ ] Expand automated test coverage (currently smoke + count assertions).

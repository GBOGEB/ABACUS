<!-- markdownlint-disable MD013 -->
# MINERVA P&ID — where it lives now (split pointer)

> Added by the **W010 / INT-001** cross-repo integration wave (2026-10-26, as `gbogeb`).
> Navigation pointer only — not an assertion that any PR is merged.

The `MINERVA_PID/` subproject was **moved out of this public tree** on 2026-10-25
(commit [`d3195298`](https://github.com/GBOGEB/ABACUS/commit/d31952981e1a78b41046aee51648c13d31862556),
`chore(minerva): move MINERVA_PID subproject to a private repo`). It no longer
exists on `ABACUS:main`. This page records where its two concerns now live, so the
public tree stays honest after the removal.

## Split (centres of excellence)

| Concern | Home | What it is |
|---|---|---|
| **Pipeline / tooling** — "how to extract, rewrite and reproduce" | **`GBOGEB/MINERVA_PID`** (private engine repo) | `src/`, `generator/`, `segmentation/`, `configs/`, `make.sh`, tests, CI — the extraction/reproduce engine. |
| **Artefact asset** — binary outputs + interactive HTML viewer (legend + layer toggles) | **`GBOGEB/cryoplant-project:assets/minerva_pid/`** | Browsable viewer, layered atlas SVGs, W002–W009 reports, with `PROVENANCE.md` linking back to the producing commits. |

## Reproducibility link-back

- Asset source: `GBOGEB/MINERVA_PID@446dfc5` (`main`).
- Last ABACUS-resident MINERVA wave: W009 commissioning, PR #559
  ([`a517d962`](https://github.com/GBOGEB/ABACUS/commit/a517d962ea09b29baa349de9436170b6fed215bd), merged).
- The cryoplant mirror carries the full provenance table and regeneration steps in
  `assets/minerva_pid/PROVENANCE.md`.

## Owner decision still open

The owner's stated intent was that the **pipeline stays on ABACUS** while only the
**asset** moves to cryoplant-project. In practice the *entire* subproject (tooling +
assets) was moved to the dedicated private engine repo `GBOGEB/MINERVA_PID`. W010 did
**not** force the pipeline back into ABACUS. Decide whether to (a) keep the dedicated
private engine repo as the pipeline home (matches the "centres of excellence" model),
or (b) re-host the pipeline in ABACUS. See the W010 integration plan for detail.

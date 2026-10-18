# CODE PURPLE — W10 Global SPINE observatory

**Review candidate only.** Read-only publication built from native snapshots of three independent GitHub repositories. This directory is an additive projection under ABACUS G3C-S, not a new engineering truth, admission register, worker authority or CI bypass.

## Open and inspect
- [Interactive offline dashboard](./index.html): four KPI cards with N−1/N/N+1 denominator labels, colored 373 closed / 105 open = 478 ordinary issues, detailed owner/cohort breakdown, fine-grained integer uncovered-debt graph, 24 verified asset deeplinks, importer, sliders and export.
- [Pinned frozen history](./W10_FROZEN_HISTORY.json): immutable native source observation before any later refresh.
- [Lossless handover](./W10_HANDOVER.md): source clocks, methodology, actual folders/repo boundaries and separate next execution work.
- [Editable repository wireframe](./REPO_ASSET_SPINE.mmd): ABACUS, CODEX, QPS typed nodes/edges.
- [Publication drift](./DRIFT_AT_PUBLICATION.md): observed newer main SHA and why the pinned snapshot is not live.

## Repeat from this wave
The standalone W10 release bundle delivered with the session also contains the **Python renderer**, **read-only GitHub refresh collector**, test suite, SVG/DOT diagrams, browser QA receipt and archived screenshots. The exact executable scripts are packaged there; **they have not been published as executable code in this source-only PR**. Do not claim repository-native recursive execution from this HTML alone.

From an extracted W10 bundle containing all source files in one directory:

```bash
python -m unittest -q test_w10_spine
python build_global_spine_w10.py --history CODE_PURPLE_W10_SPINE_HISTORY.json
GITHUB_TOKEN='<optional read-only credential>' python refresh_w10_spine.py --out W10_NEXT_SNAPSHOT.json
```

The HTML supports **Import snapshot** to view a new JSON source-reported observation without replacing the original; **Export handover state** saves current operator scenario and imported observations; **Reset** restores the immutable bundle snapshot. Upload the newly acquired snapshot manually into HTML and record its verified exact-source state before accepting numbers. No browser credential handling or automatic GitHub mutation.

## Measurement integrity
Original source epochs in the HTML were verified separately. N−1→N workflow populations differ; N+1 values are conditional scenarios, not statistical predictions. Latest main at the frozen observation **1122dca15557e4d2b0ec16300fcbf409db678e86** had B0 RED and no qualified current-main coverage; **67.345%** is last independently green main (SHA **97a8b13faff577272a90edaf0dd4593035e10605**). Ordinary issue closure is not causal root closure. No Crew launch or accepted REX is inferred.

Canonical issues: [ABACUS #1860](https://github.com/GBOGEB/ABACUS/issues/1860) and [CODEX #977](https://github.com/GBOGEB/CODEX/issues/977).

**MERGE_ADMISSION=HOLD · SECURITY_WAIVER=false · AUTHORITY_TRANSFER=false**

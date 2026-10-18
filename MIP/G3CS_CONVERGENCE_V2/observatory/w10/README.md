# CODE PURPLE — W10 Global SPINE observatory

**Review candidate only.** Read-only publication built from native snapshots of three independent GitHub repositories. This directory is an additive projection under ABACUS G3C-S, not a new engineering truth, admission register, worker authority or CI bypass.

## Open and inspect
- [Interactive offline dashboard](./index.html): four KPI cards with N−1/N/N+1 denominator labels, colored 373 closed / 105 open = 478 ordinary issues, detailed owner/cohort breakdown, fine-grained integer uncovered-debt graph, 24 verified asset deeplinks, importer, sliders and export.
- [Pinned frozen history](./W10_FROZEN_HISTORY.json): immutable native source observation before any later refresh.
- [Lossless handover](./W10_HANDOVER.md): source clocks, methodology, actual folders/repo boundaries and separate next execution work.
- [Editable repository wireframe](./REPO_ASSET_SPINE.mmd): ABACUS, CODEX, QPS typed nodes/edges.
- [Publication drift](./DRIFT_AT_PUBLICATION.md): observed newer main SHA and why the pinned snapshot is not live.

## Repeat from this wave
W11 now commits the **Python renderer**, **read-only GitHub refresh collector**, W10/W11 regression suites, typed DAG/SIPOC contract, generated read-only JSON receipts and the root-level B0 discovery bridge. The standalone bundle retains browser QA sources and screenshots; its local reproducibility is **not** the same as native exact-head admission. The scripts are committed in this review branch; claim native qualification only after terminal exact-head CI, not from this HTML alone.

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


## W11 executable evidence contract and native-test bridge

See [W11 lossless handover](./W11_HANDOVER.md), [typed DAG](./SPINE_DAG_W11.json),
[five-row SIPOC](./SPINE_SIPOC_W11.json) and
[fail-closed contract](./SPINE_CONTRACT_W11.json). Rebuild:

```bash
cd MIP/G3CS_CONVERGENCE_V2/observatory/w10
python spine_contract.py --history W10_FROZEN_HISTORY.json --outdir .
python build_global_spine_w10.py --history W10_FROZEN_HISTORY.json --outdir .
python -m unittest discover -p 'test_*.py' -v
```

ABACUS root [canonical B0 collector bridge](https://github.com/GBOGEB/ABACUS/blob/docs/w10-global-spine-observatory-20261018/tests/test_g3cs_spine_w11_bridge.py)
exposes the nested W7 postmerge cases and W10/W11 regressions as independent native JUnit test methods. Exact-head GitHub results and measurable coverage uplift remain pending. The workflow's mandatory security/Safety gate stays unchanged.

W11 module **local scoped**: 177/177 covered statements and 26/26 covered arcs (100% source-local); this is not a measurement of full main. W10 issue and coverage numbers remain pinned to the historical source SHA until a new native-consistent epoch is added.

`MERGE_ADMISSION=HOLD` / `SECURITY_WAIVER=false` / `AUTHORITY_TRANSFER=false`.

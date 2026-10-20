# CODE PURPLE W13 — weighted neural SPINE, SIPOC, gg_MATH view

**Review-only, additive** to the combined W10–W12 dashboard under ABACUS \`MIP/G3CS_CONVERGENCE_V2/observatory/w10\`. Generated HTML is a read-only projection; it cannot authenticate a worker, override owner authority or authorize merging.

## Reproducible asset chain

\`\`\`text
Original 37-node/46-edge pinned ABACUS DAG + 5-row SIPOC
     └── build_spine_neural_w13.py (source compiler)
          ├── 10 derived S/C satellites
          ├── 1 gg_MATH pinned repo + 7 provider method references
          ├── 3 proposed metadata-only federation-route edges
          ├── W13_NEURAL_SPINE_DATA.json [55 nodes / 73 edges]
          └── neural_spine_w13.template.html
                └── W13_NEURAL_SPINE_INTERACTIVE.html
                      ├── 62% initial density (34/55 visible)
                      ├── family numeric IDs + source link/full registry
                      ├── node diameter: total / in / out / betweenness
                      ├── edge width: downstream structural reach / uniform
                      ├── typed edge/node filters
                      ├── selected-neuron upstream/downstream inspector
                      └── sticky desktop legend, mobile stacked details
\`\`\`

The sources \`SPINE_DAG_W11.json\` and \`SPINE_SIPOC_W11.json\` are **reused in place**; this PR does not create a competing authoritative copy. A separate gg_MATH source-owned PR provides the GoGREEN travel-card Python/YAML and the provider-side native mathematical tests.

## Interpretation and traceability

- Node *fill* encodes repository/asset/stage/supplier/customer/method type.
- Node *ring* encodes relative in/out balance. **Diameter** changes with actual modeled in-degree/out-degree. Source graph maxima: **7 inbound and 16 outbound**.
- Edge color encodes OWNS, SOURCE_INPUT, DERIVES, OBSERVATION_ONLY, SIPOC_SUPPLIES, SIPOC_SERVES, MATH_REFERENCE or FEDERATION_REFERENCE. Width is derived from *modeled downstream reach* — **not** actual run or failure frequency, which remains UNKNOWN.
- Every original node retains its full name, source owner, exact pinned SHA and originating path; each SIPOC S/C satellite retains the five-row ID. Method URLs point to gg_MATH historical provider SHA.
- BRIDGE/TUNNEL/TELEPORT/FEDERATION are descriptive metadata hops, **not actual data movement or authority transfer**.
- The node-set grows from **37 to 55** and edge-set **46 to 73**, from explicitly typed synthetic satellites/links. Those additive nodes are not repository-native execution objects.

## Build, test and inspect

From the ABACUS repository root:

\`\`\`bash
root=MIP/G3CS_CONVERGENCE_V2/observatory/w10
python "$root/build_spine_neural_w13.py" \
  --dag "$root/SPINE_DAG_W11.json" \
  --sipoc "$root/SPINE_SIPOC_W11.json" \
  --template "$root/neural_spine_w13.template.html" --outdir "$root"
python -m unittest discover -s "$root/tests" -p test_neural_spine_w13.py -v
\`\`\`

Python 3.11 and 3.12 exact-head CI qualification defined in \`.github/workflows/w13-neural-spine.yml\` must independently verify original generated JSON/HTML byte parity, at least 25 tests and scoped branch coverage. Browser screenshots and \`W13_BROWSER_QA.json\` are **LOCAL_REPRODUCIBILITY** only. One root B0 discovery bridge extension exposes 25 individual test methods without culling existing tests; the exact-head native collected test count remains UNKNOWN until terminal original JUnit evidence is read.

## Next bounded DoD and governance

1. Qualify native CI from this PR's **exact head**, original job/run/attempt and artifact digest. Repair first red on source-owning scope only; never weaken Safety.
2. Reconcile new W13 source scope vs current-main coverage using same selection/tool/eligible denominator; do not add overlapping PR gains.
3. Preserve global family roll-up. A graph count (55) is not a root census or issue denominator (historical three-repo 478 ordinary issues is a separate cohort).
4. Source-owner review, effective mandatory required contexts, eligible independent review, last-push/thread protection and **blocked RED canary** are independent P0 admission gates. Do not infer review from a merge event.
5. Consume gg_MATH travel-card receipts only when route validation and actual authentic execution evidence are independently supplied.

\`MERGE_ADMISSION=HOLD\` · \`SECURITY_WAIVER=false\` · \`AUTHORITY_TRANSFER=false\` · \`CREW_LAUNCH=UNKNOWN\` · \`REX_ACCEPTED=UNKNOWN\`.

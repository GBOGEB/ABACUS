# W79 deterministic multivariate analysis

W79 is the bounded follow-on to the executed W78 deterministic-work diversity gate.

## Entry evidence

- W78 workflow run: `34777543492`
- W78 evaluated head: `9d55b8ba73a05efaa3e519acacacd1dffb3c787c`
- exact source states: 15
- deterministic replays: 2 per source state, `PASS_15_OF_15`
- distinct full work states: 15
- distinct semantic-work states: 10
- centered full-work rank: 9
- centered semantic-work rank: 7
- W78 diversity artifact: `10323323552`
- artifact digest: `sha256:6e0a868916c1730fdc8eefc1f24ffea06185ca56ef1a8caffdaeb325eed445ae`

## W79 method

The primary panel is the seven-dimensional semantic-work vector. The ten-dimensional full deterministic-work vector is a sensitivity panel. Each panel uses `log1p` transformation, column z-scoring with `ddof=1`, PCA on the resulting correlation structure, and a fixed-seed 95th-percentile normal-random parallel analysis (`2000` replicates, seed `7901`). Constant dimensions are removed explicitly and reported.

The workflow recomputes all 15 W78 exact historical source states rather than trusting a copied summary. NumPy is pinned to `2.3.3`; GitHub Actions are pinned to immutable commit SHAs; pull-request execution checks out the exact PR head rather than the synthetic merge ref.

## Authority boundary

W79 is `derived_operational_analysis` only. PC scores and loadings are descriptive diagnostics, not Bradley-Terry results and not autonomous allocation instructions. BT and reverse-BT remain withheld until an observed pairwise outcome graph exists. W79 cannot grant QPS engineering, compliance, release, acceptance, negotiation, Table-10, or Grand-Mission credit and cannot compensate `GBOGEB/cryoplant-project#923`.

# ABACUS root-depth census and integration gaps

Evidence date: 2026-10-22. Exact observed main:
`44caccf716a7c20693a2911566289bfc75ea81d9`.

Source: GitHub REST recursive Git tree, `truncated=false`.
This is a **tracked-tree census**, not a local filesystem,
ZIP/release-asset inspection, semantic orphan determination,
or governed coverage report.

## Actual measured Git-tree population

| Category | Count |
| --- | ---: |
| Git tree entries | 4,673 |
| Tracked blobs | 4,055 |
| Directories | 618 |
| Python (.py) | 1,345 |
| YAML + YML | 655 |
| JSON | 531 |
| Markdown | 1,015 |
| Mermaid (.mmd) | 26 |
| Graphviz (.dot) | 9 |
| TOML | 4 |
| INI | 1 |
| Active GitHub workflow YAML/YML paths | 214 |
| Gitlinks (160000 submodules) | 0 |
| Tracked nested .git paths | 0 |

The complete recursive tree has no tracked files ending in
.pdf, .pptx, .docx, .xlsx or .zip. `Artifact_Builder.ipynb` is
tracked, along with one PNG and SVG vector drawings.
This is expected to differ from local/controlled binary storage.

The root `.gitignore` deliberately ignores most binaries
(PDF, Word, Excel, PowerPoint, archives, raster images), venvs
and local test evidence. A tracked-tree scan cannot show
ignored local files, Release assets or archive members.
Never equate zero Git-tracked ZIPs with zero external ZIPs.

## Embedded project boundaries, not proven Git submodules

The full tree contains nested manifest candidates:

- `MINERVA_PID/pyproject.toml`: dedicated Python package,
  its own `.coveragerc`, and direct-run standalone tests.
  Explicit `MINERVA_PID/AGENTS.md` says its tests are not pytest.
- `qps_slide_reviewer/package.json`: independent Next.js app.
- `qps_contract_canonicalization/package.json`: Node project.
- `deepagent-handover-package/implementation/deepagent/package.json`:
  TypeScript package, currently has a placeholder test command.
- `tools/everred_v3/pyproject.toml`: scoped isort configuration;
  a local config island, **not by itself** a separate package.

No Gitlink was present in the exact tree, so none is reported as
a confirmed Git submodule. Ignored local `.git` directories
cannot be discovered by examining remote tracked blobs.

## Coverage reconciliation — do not subtract populations blindly

Historical W46 report-only B0: 223 measured paths, 114 zero
executed, 9,430 / 28,014 combined covered opportunities,
18,584 missing. Historical HEAD differs from this tree.

Current tree: 1,345 tracked Python paths, including generated,
optional, test and standalone components. The apparent
`1345 - 223 = 1122` path delta is only a **cross-scope
discovery question**. It is not 1,122 verified missing assets.

Canonical root `pytest.ini`: tests under `tests` and
`DMAIC_V3/tests`; `norecursedirs` includes `qplant`,
`deepagent-handover-package` and `DMAIC_V3`, requiring
explicit collection/runner precedence testing.
Standalone `MINERVA_PID` test scripts are a separate cohort.
Main `pyproject.toml` setuptools includes `DMAIC_V3`
as published package; other root scripts are not thereby
automatically published.

Per-project acceptance is required:
- tracked source paths (complete tree population);
- discovered runtime entrypoints/imports (static + dynamic);
- tests collected and tests actually executed (distinct);
- instrumented sources and coverage contexts (same head);
- excluded/intentionally external/unknown paths (explicit);
- artifacts produced/consumed with hashes and owner;
- real consumer smoke test for each retained capability.

## Byte duplication and large artifacts

The source tree has 62 duplicate Git blob groups containing
175 file entries, with 17,288,878 repeated tracked bytes,
based on exact Git blob SHAs. This is byte identity, not
behavioral equivalence or removal authority.

Examples: four identical QCELL-LB SVG source/extract copies,
duplicated tracker YAML, repeated archived JSON snapshots,
duplicated historical reports. Preserve source-of-record
ownership and emitted artifact lineage before consolidating.

`DMAIC_V2.3_INTEGRATION_REPORT_20251108_202022.md` is
43,646,140 bytes. The `MINERVA_PID` root is approximately
51.75 million uncompressed tracked bytes, primarily drawing
assets, not an orphan-code counter. These warrant I/O and
artifact-lineage investigation, not indiscriminate test work.

## Root-level syntax and lint/format crosswalk

| Kind | Executable check | Formatting policy |
| --- | --- | --- |
| YAML/YML | BaseLoader compose, duplicate keys, job needs DAG | yamllint separately; do not rewrite Actions blindly |
| GitHub Actions | PyYAML BaseLoader then actionlint (separate) | Preserve literal `on`, expressions, jobs, triggers |
| JSON | strict stdlib decoder with duplicate-key guard | json formatting only on owner-controlled inputs |
| TOML | Python 3.11 `tomllib` parse | owner-selected TOML formatter; preserve semantics |
| INI | `configparser` syntax | avoid silent interpolation/reordering |
| `__init__.py` | AST parse only; no imports/side effects | Black/isort limited to controlled source diff |
| Mermaid `.mmd` | external `mmdc` required | semantics UNKNOWN without renderer |
| Graphviz `.dot` | external `dot` required | semantics UNKNOWN without parser |
| CSV/SVG/HTML | explicit schema/consumer QA later | do not label unvalidated output GREEN |

The existing changed-doc gate handles Markdown/YAML/JSON and
`.pre-commit-config.yaml` declares `check-toml`, but the
changed-doc workflow does not currently run TOML, INI, Mermaid
or Graphviz checks. Parsing is not equivalence or integration.

Read-only scanner:

```bash
git rev-parse HEAD
gh api "repos/GBOGEB/ABACUS/git/trees/$(git rev-parse HEAD)?recursive=1" > tree.json
python tools/triage/root_depth_census.py --tree tree.json \
  --head "$(git rev-parse HEAD)" --out root_depth.json
python tools/triage/config_surface_audit.py --root . \
  --out config_surface.json
```

No automatic YAML formatter, security waiver, policy mutation,
runner dispatch, archive extraction, merge or pruning.

## Highest-ROI next wave (disjoint proposals)

A: investigate the independent MINERVA_PID test runner and
cross-population coverage interface; never merge denominators.
B: deep YAML DAG inventory (214 Actions workflows) and
separate parser/style/execution lints, ensuring no false GREEN.
C: attach ownership/contract receipts for duplicate Git blobs.
D: compare root Python/other project runtime entrypoints against
test collection and import graph with unknowns retained.
E: inventory ignored local/document binaries in an explicitly
authorized, privacy-safe workspace, not this public repo.

Merge admission remains HOLD. DoV and coverage uplift UNKNOWN.

# Binary engines (DOW)

Read-only engines that take stock of a folder of office files, drawings and archives, read their structure, and
propose (never perform) how to tidy them. They sit next to `DMAIC_V3/tools/dow_engine.py` and `keb_engine.py`: what
they extract is candidate knowledge for the DOW knowledge extractor, never accepted knowledge.

Nothing here contains data. Site-specific values live in a private configuration, and every output goes to a data
folder outside the repository.

## What the engines do

| Engine | Stages | What it does |
|---|---|---|
| `estate_inventory.py` | E0-E2 | Lists the top-level files of one root (and the `GG_*` folders it created), proves each type from its bytes, hashes it, sorts it by type (A-K) and epic, finds duplicates and older versions, and ranks ZIP families by reverse Kahn (newest tip first). |
| `estate_probe.py` | E3-E4 | Opens each file read-only and extracts structure: outline, bullet and number levels, fonts, colours, sizes, text boxes, tables, formulas, TOC, connectors as graph edges. Files with no epic by name are re-sorted by their text. Stored text samples are scrubbed of secret-shaped strings. |
| `estate_scaffold.py` | E5 | Writes one `TYPE.gg_Engine` folder per type (manifest, capability matrix, SIPOC per lane, queue, skill, rules, ADR) and the estate graph. |
| `estate_moveplan.py` | E6 | Proposes a destination for every file and says why a file is held back (git-tracked, open in Office, online-only, path too long, destination exists). |
| `Invoke-EstateMove.ps1` | E7 | Applies the move plan. Dry run unless `-Execute`; re-checks hash, lock and destination before each move and logs each move as it happens, so any run can be undone (`-Undo`). |
| `deep_graph.py` | E4-E5 | Reads drawings (PPTX, SVG, VSDX, drawio, Mermaid, SVG inside HTML) into one graph format: nodes, edges with direction, legend, styles, QA. |
| `slide_atlas.py` | E4-E6 | Compares every slide of every deck: exact copies, restyles, remakes (before/after), slide families, style flags. Writes a static compare page. |
| `reference_test.py` | E8 | Scores the drawing reader: R1 answer key, R2 crosswalk, R3 adversarial (must not guess), R4 read-only, R5 hand-labelled pilot. |
| `thread_promote.py` | E9 | The only way a candidate link becomes accepted (see below). |
| `html_shot.py` | E8 | Renders HTML pages in Chromium (Playwright) and reports console errors and overflow. |
| `public_safety_scan.py` | gate | Checks files before they go to a public repository: private markers, user paths, secret-shaped strings, Python that only parses on 3.12+. |
| `estate_spec.py` | - | The one source of types, lanes, the DAG, capabilities, and the configuration loader. |
| `git_readonly.py` | - | Reads HEAD, tracked paths and bundle heads from disk. git is never run, so an inventory cannot write into a checkout. |
| `ggmath_bridge.py` | - | Loads the gg_MATH kernels at a pinned commit (see below). |

## The E0-E9 DAG and the lanes

```mermaid
flowchart LR
  E0[E0 discover] --> E1[E1 identify] --> E2[E2 classify] --> E3[E3 parse] --> E4[E4 extract] --> E5[E5 semantic]
  E5 --> E6[E6 decide]
  E2 --> E6
  E6 --> E7[E7 write / patch]
  E7 --> E8[E8 QA]
  E4 --> E8
  E8 --> E9[E9 receipt / release]
```

| Lane | Stages | Core function |
|---|---|---|
| L1 intake | E0-E2 | discover, identify (bytes, not extension), hash, dedupe, lock detection |
| L2 read and parse | E3 | open read-only, parse package parts, slice into pages, slides, sheets, sections |
| L3 extract | E4 | levels, fonts, colours, sizes, text boxes, shapes as a graph |
| L4 semantic | E5-E6 | meaning, links, staleness, a decision per file |
| L5 write and patch | E7 | copies only; originals are never overwritten |
| L6 QA and release | E8-E9 | checks, receipts, release |

Decisions at E6: `KEEP_CANONICAL`, `REWORK`, `SUPERSEDED`, `STALE_ARCHIVE`, `DUPLICATE`, `ACTIVATE_ZIP`, `PARK`.

## Pathways

A pathway is what a person asks for; it runs the stages it needs, in DAG order. Run the engines in this order
(every command is read-only except the last one with `-Execute`):

| I want | Run |
|---|---|
| what is in this folder, by type and epic | `estate_inventory.py --root-id ID` |
| the structure of the files | the above, then `estate_probe.py --root-id ID` |
| the engine folders and the estate graph | the above, then `estate_scaffold.py` |
| a tidy plan (nothing moves) | the above, then `estate_moveplan.py --root-id ID`, then `Invoke-EstateMove.ps1 -RootId ID` |
| to move the safe files | the dry run above, read it, then `Invoke-EstateMove.ps1 -RootId ID -Execute` (owner only) |
| which ZIPs are dormant worktrees or handovers | `estate_inventory.py`; read `zip_reverse_kahn.json` |
| every drawing as nodes and edges | `estate_probe.py`, then `deep_graph.py --root-id ID --redraw` |
| copied, restyled or remade slides | `estate_scaffold.py`, then `slide_atlas.py` |
| whether the drawing reader guesses | `reference_test.py` |

Run each one as `python -I -X utf8 DMAIC_V3/binary_engines/<engine>.py ...` (`-I` keeps the environment from
changing what is imported; `-X utf8` keeps non-ASCII file names printable). The runner that chains them and writes
receipts is not part of this folder.

## Configuration and data: ESTATE_CONFIG and ESTATE_HOME

| Variable | Default | Holds |
|---|---|---|
| `ESTATE_HOME` | `~/.binary_estate` | every output: `inventory/`, `roots/<id>/inventory/`, `deep/`, `engines/`, `graph/`, `fixtures/`, `pilot/`, the gg_MATH cache. Must be outside the repository: the engines refuse to start otherwise, because outputs name the files they read. |
| `ESTATE_CONFIG` | `$ESTATE_HOME/estate_config.yaml`, else `estate_config.example.yaml` | roots and their depth, epics and keywords, personal tokens, private markers, references and pilot files. Copy the example, edit it, keep it private. |
| `ESTATE_LEGEND_REGISTRY` | `$ESTATE_HOME/LEGEND_REGISTRY.yaml` | owner-accepted legend rules. `LEGEND_REGISTRY.example.yaml` is a template and is never read as rules. |
| `GG_MATH_HOME` | not set | a gg_MATH checkout, read once to fill the kernel cache. |

Root depth decides how much runs: `full` hashes everything and probes, `standard` hashes files up to 200 MB and
probes, `light` hashes but does not probe.

## Evidence and DEFER

The readers report what is drawn, not what it means.

* An edge is `bound` when the file attaches both ends, `geometric` when each end lands on a shape, `half` or
  `unresolved` otherwise. Its evidence is `FILE_CONNECTED`, `GEOMETRIC_TOUCH`, `PARTIAL` or `NONE`.
* An arrowhead gives a drawn direction, not a flow. A short arrow drawn on a line (a flow marker) gives that line its
  direction.
* An edge's `semantic_type` stays `DEFER` unless an in-drawing legend or an owner-accepted rule types its style. A
  dashed line or a colour means nothing by itself. A legend entry must be a short label next to a symbol; a style
  that a legend maps to two meanings stays `DEFER`.
* An end floating inside a large container is not attached; it must touch the container's border.
* A raster image wrapped in SVG is flagged, not read as vectors. Unsupported files are reported, never guessed.
* `UNKNOWN` is never `PASS`. Reference tests without an answer key, crosswalk or reviewed pilot labels report `DEFER`.

## Mycelium and golden thread

Two levels of links, and one rule for moving up:

* **Mycelium**: `deep/keb_candidates.jsonl`, every candidate link with its evidence. Regenerated on each read.
  Nothing in it is accepted.
* **Golden thread**: `GOLDEN_THREAD.jsonl` in `ESTATE_HOME`, accepted links only. Append-only, never regenerated,
  never written by a reader.

`thread_promote.py promote <locator> --authority <who> --evidence <where> --relation <type>` moves a candidate up.
It refuses without an authority and evidence, refuses a relation that is still `DEFER` (the authority types it; the
tool never does), refuses geometry-only evidence unless `--reviewed` (a person looked at the drawing), and refuses
a link that is already accepted for that file version.

## The math: gg_MATH kernels, imported at a pinned commit

Similarity (shingles, Jaccard, overlap, containment, MinHash, LSH bands, union-find) comes from
`GBOGEB/gg_MATH kernels/set_similarity.py`; geometry (SVG transforms, point in box, distances, endpoint snap, flow
direction) from `kernels/plane_geometry.py`. The engines decide policy (thresholds, the tuning rules, DEFER); the
kernels only compute.

gg_MATH is not a pip package. `ggmath_bridge.PINS` names the commit, path, git blob id and sha256 of each kernel;
`load()` builds the module from exactly those bytes, held in memory, or fails closed. Bytes come from the cache in
`ESTATE_HOME`, else from `GG_MATH_HOME`. Nothing is downloaded and git is never run. To move a pin, check out the new
commit in `GG_MATH_HOME`, run `python -I DMAIC_V3/binary_engines/ggmath_bridge.py pin`, and update `PINS` and
`GG_MATH_COMMIT` in `.github/workflows/binary-engines.yml` together (a test keeps them equal).

Topological layering is not owned here either: the hub owns it (`topo_layers`). Until ABACUS has a pinned bridge to
the hub, `estate_inventory.reverse_kahn` keeps its local layering, marked with a TODO that names the owner.

## Tests

```bash
python -m pip install -r requirements-binary-engines.txt
GG_MATH_HOME=<gg_MATH checkout at the pinned commit> python -X utf8 -m unittest discover -s tests/binary_engines -t . -v
```

The tests use only the example configuration and synthetic fixtures. Without the libraries or the kernels they
skip; `BINARY_ENGINES_REQUIRE_DEPS=1` (set in the `binary-engines` workflow) turns every skip into a failure.

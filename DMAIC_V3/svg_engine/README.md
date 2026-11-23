# SVG-ENGINE (DOW engine)

Source-faithful diagram ingress and layered redraw with provenance. It
reads a native Inkscape SVG (and PPTX review decks) as XML, keeps every
native layer identity, and redraws to a PDF whose Optional Content Groups
behave exactly like the source's layer visibility. Every redraw is checked
against an independent oracle.

Evidence class of every output: `REVIEW_ONLY`. Nothing here grants
engineering approval or release admission.

Location: `DMAIC_V3/svg_engine/`, next to the DOW and KEB engines in
`DMAIC_V3/tools/`. Import it as `DMAIC_V3.svg_engine` from a repository
checkout on `sys.path`. The `abacus-dow` wheel packages only the top-level
`DMAIC_V3` modules, not its subpackages.

## Modules

- `ingress` (W1): parse SVG with no entities and no network, fail closed on
  unsafe content, native layer tree, operating-state guard.
- `paint_runs` (W1): split paint order at nested-layer boundaries, so each
  contiguous paint run has one owner layer.
- `pdf_ocg.build_nested_ocg_pdf` (W2): layered PDF with true parent
  semantics (nested `/OC BDC`), nested Layers panel, multi-page presets.
- `pdf_ocg.build_flat_ocg_pdf` (W1): flat-OCG baseline, kept as the
  "no default-visibility leakage" reference.
- `fidelity.check_pdf_fidelity` (W2): structural, visual and semantic redraw
  checks against an SVG oracle (QA ladder below).
- `ooxml_geometry.analyse` (W2): PowerPoint frame-model group geometry and
  effective font chain.
- `ooxml_inventory` (W1): OOXML object and media inventory, out-of-slide and
  overlap candidates, tag crosswalk, layer CSV reconciliation.
- `ooxml_qa` (W2): adapter vs PowerPoint COM oracle; W1-vs-W2 regression.
- `page_identity` (W2): which source or layer state each page of an
  authored PDF shows, by native text tokens.
- `fixtures` (W2): synthetic PPTX (3-deep groups, scale, rotation, flips,
  font inheritance) and a synthetic layered SVG.
- `oracles/ppt_com_oracle.ps1` (W2): PowerPoint's own geometry and fonts
  through COM (Windows-only verification lane).

## Use

```python
from DMAIC_V3.svg_engine.fidelity import check_pdf_fidelity
from DMAIC_V3.svg_engine.ingress import load_svg
from DMAIC_V3.svg_engine.pdf_ocg import build_nested_ocg_pdf

root, raw = load_svg("drawing.zip", member="drawing.svg")  # or an .svg
presets = {
    1: {"title": "As authored", "skip_subtrees": [], "force_on": []},
    2: {"title": "Variant", "skip_subtrees": ["L1"], "force_on": ["L9"]},
}
pdf = "out/drawing_layers.pdf"
build = build_nested_ocg_pdf(root, pdf, page_presets=presets,
                             source_bytes=raw)
receipt = check_pdf_fidelity(pdf, build, root, authored_pdf="authored.pdf")
assert receipt["summary"]["FAIL"] == 0
```

CLI: `python -m DMAIC_V3.svg_engine --help` (`nested-pdf`, `flat-pdf`,
`fidelity`, `ooxml-geometry`, `ooxml-qa`, `fixture`, `page-identity`).

Project-specific inputs (layer IDs for presets and demonstrations, file
names, anchor patterns) are parameters. They live with the owning project,
never in this package.

Dependencies are pinned in `requirements-svg-engine.txt`: `lxml`,
`PyMuPDF`, `CairoSVG` (needs libcairo), `numpy` and `python-pptx`. On
Windows, set `SVG_ENGINE_CAIRO_BIN` to a folder holding `libcairo-2.dll`
(for example Inkscape's `bin`), and optionally `SVG_ENGINE_DEPS` to a
`pip install --target` folder.

## Method

**Layer identity is the native ID, never the label.** Labels repeat across
sub-systems; keying by label silently drops layers and pools their content.

**PDF parent semantics use nested `/OC BDC`, not OCMD.** Each paint run is
wrapped in one `/OC /L_<id> BDC … EMC` per native layer on its ancestor
chain. Under ISO 32000 8.11.3.2, nested optional content shows only when
every enclosing group is ON, which is Inkscape's `display:none`
inheritance. Each OCG defaults to the layer's *own* style, so a parent
switched OFF then ON restores each child's own state. MuPDF ignores
`/OCMD` on form XObjects, so OCMD-based hierarchies degrade to flat
switches there.

**PowerPoint group geometry uses the frame model, not affine
composition.** PowerPoint maps each group to an absolute frame, scales the
children's unrotated boxes axis-wise into it, then flips and rotates about
the frame centre. A non-uniform group scale never shears a rotated child.
A pure affine composition disagrees with PowerPoint by millimetres.

**Font substitution is a silent fidelity loss.** K4106 checks embedded
font families against the families the source requests.

## QA ladder

`fidelity.check_pdf_fidelity` runs these checks:

- Structural
  - K4001: OCG count equals the native layer count.
  - K4102: OCG defaults equal each layer's own source style.
  - K4111: the `/Order` tree mirrors the native hierarchy.
  - K4303: page count equals the authored PDF.
- Visual
  - K4201: default page 1 equals the source SVG (same renderer chain).
  - K4304: each preset page equals the source with that preset.
  - K4105: no default-visibility leakage against the flat baseline.
  - K4302 / K4305: authored-PDF cross-renderer parity (at least 0.99,
    otherwise DEFER).
- Semantic
  - K4112: every single switch matches the source with that layer flipped.
  - K4113: parent OFF hides its subtree; ON restores own child states.
  - K4114: switching on a source-hidden parent shows its children by
    their own states.
  - K4106: embedded fonts are the requested families.
- Provenance
  - K5001: the built PDF's SHA256 equals the build report.

Pixel comparisons run at 45 dpi. A pixel matches when every channel is
within ±22; a page matches when at least 0.99999 of its pixels match.

## Origin and the DOW / gg_MATH split

Landed from the owner-private SVG-ENGINE W1 package (ZIP SHA256
`2b41da77…c5b4e`, 28/28 internal hashes verified) and W2 package (dated
2026-11-12, all 37 internal hashes verified). Both packages stay private.
W2 already imported W1's ingress and splitter; here both live in one
package and W2 imports W1 in-package. On the original owner-private drawing
this package reproduces W2's nested PDF byte for byte and its 63/63 switch
result. That receipt stays with the private evidence, not here.

Routing rule: engines go to DOW (this repository) unless they are
math-driven, which go to `GBOGEB/gg_MATH`.

- All modules stay in DOW. They are format adapters, builders and QA:
  parsing, PDF and OOXML object models, rendering oracles.
- `ooxml_geometry.map_into_frame` also stays in DOW. It is the one geometry
  kernel (about 15 lines), but it encodes PowerPoint's frame *semantics*,
  an application rule verified against PowerPoint, not general transform
  mathematics. gg_MATH has no 2D frame or affine kernel to import (only
  triangle meta-transforms), and splitting this out would add a cross-repo
  import for one application-specific function. Revisit if gg_MATH gains a
  general 2D transform kernel.

These did **not** land here: the project-specific receipt composer, the
project HTML explorer upgrade, the browser QA of that explorer, and the
project-specific K-series counts. They encode one owner-private drawing
(layer IDs, labels, tags, file names) and stay with that project's private
evidence.

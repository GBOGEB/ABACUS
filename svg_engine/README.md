# SVG-ENGINE (DOW engine)

Source-faithful diagram ingress and layered redraw with provenance. It reads a native Inkscape SVG (and PPTX
review decks) as XML, keeps every native layer identity, and redraws to a PDF whose Optional Content Groups
behave exactly like the source's layer visibility. Every redraw is checked against an independent oracle.

Evidence class of every output: `REVIEW_ONLY`. Nothing here grants engineering approval or release admission.

## Modules

| Module | Wave | What it does |
|---|---|---|
| `ingress` | W1 | Parse SVG (no entities, no network), fail closed on unsafe content, native layer tree, operating-state guard |
| `paint_runs` | W1 | Split paint order at nested-layer boundaries: one owner layer per contiguous paint run |
| `pdf_ocg.build_nested_ocg_pdf` | W2 | Layered PDF with true parent semantics (nested `/OC BDC`), nested Layers panel, multi-page presets |
| `pdf_ocg.build_flat_ocg_pdf` | W1 | Flat-OCG baseline, kept as the "no default-visibility leakage" reference |
| `fidelity.check_pdf_fidelity` | W2 | Structural, visual and semantic redraw checks against an SVG oracle (QA ladder below) |
| `ooxml_geometry.analyse` | W2 | PowerPoint frame-model group geometry and effective font chain |
| `ooxml_inventory` | W1 | OOXML object/media inventory, out-of-slide and overlap candidates, tag crosswalk, layer CSV reconciliation |
| `ooxml_qa` | W2 | Adapter vs PowerPoint COM oracle; W1-vs-W2 regression |
| `page_identity` | W2 | Which source/layer state each page of an authored PDF shows, by native text tokens |
| `fixtures` | W2 | Synthetic PPTX (3-deep groups, scale, rotation, flips, font inheritance) and synthetic layered SVG |
| `oracles/ppt_com_oracle.ps1` | W2 | PowerPoint's own geometry and fonts through COM (Windows-only verification lane) |

## Use

```python
from svg_engine.ingress import load_svg
from svg_engine.pdf_ocg import build_nested_ocg_pdf
from svg_engine.fidelity import check_pdf_fidelity

root, raw = load_svg("drawing.zip", member="drawing.svg")       # or a plain .svg
presets = {1: {"title": "As authored", "skip_subtrees": [], "force_on": []},
           2: {"title": "Variant", "skip_subtrees": ["<layer id>"], "force_on": ["<layer id>"]}}
build = build_nested_ocg_pdf(root, "out/drawing_layers.pdf", page_presets=presets, source_bytes=raw)
receipt = check_pdf_fidelity("out/drawing_layers.pdf", build, root, authored_pdf="authored.pdf")
assert receipt["summary"]["FAIL"] == 0
```

CLI: `python -m svg_engine --help` (`nested-pdf`, `flat-pdf`, `fidelity`, `ooxml-geometry`, `ooxml-qa`,
`fixture`, `page-identity`). Project-specific inputs (layer IDs for presets and demonstrations, file names,
anchor patterns) are parameters; they live with the owning project, never in this package.

Dependencies: `lxml`, `PyMuPDF`, `CairoSVG` (needs libcairo), `numpy`, `python-pptx` (pinned in
`requirements-svg-engine.txt`). On Windows set `SVG_ENGINE_CAIRO_BIN` to a folder holding `libcairo-2.dll`
(for example Inkscape's `bin`) and optionally `SVG_ENGINE_DEPS` to a `pip install --target` folder.

## Method

**Layer identity is the native ID, never the label.** Labels repeat across sub-systems; keying by label silently
drops layers and pools their content.

**PDF parent semantics: nested `/OC BDC`, not OCMD.** Each paint run is wrapped in one `/OC /L_<id> BDC … EMC`
per native layer on its ancestor chain. Under ISO 32000 8.11.3.2 nested optional content shows only when every
enclosing group is ON, which is Inkscape's `display:none` inheritance. Each OCG defaults to the layer's *own*
style, so a parent switched OFF then ON restores each child's own state. MuPDF ignores `/OCMD` on form XObjects,
so OCMD-based hierarchies degrade to flat switches there.

**PowerPoint group geometry: frame model, not affine composition.** PowerPoint maps each group to an absolute frame,
scales children's unrotated boxes axis-wise into it, then flips and rotates about the frame centre. A non-uniform
group scale never shears a rotated child. A pure affine composition disagrees with PowerPoint by millimetres.

**Font substitution is a silent fidelity loss.** K4106 checks embedded font families against the families the
source requests.

## QA ladder (`fidelity.check_pdf_fidelity`)

| ID | Family | Check |
|---|---|---|
| K4001 | structural | OCG count equals native layer count |
| K4102 | structural | OCG defaults equal each layer's own source style |
| K4111 | structural | `/Order` tree mirrors the native hierarchy |
| K4303 | structural | page count equals the authored PDF |
| K4201 | visual | default page 1 equals the source SVG (same renderer chain) |
| K4304 | visual | each preset page equals the source with that preset |
| K4105 | visual | no default-visibility leakage vs the flat baseline |
| K4302 / K4305 | visual | authored-PDF cross-renderer parity (>= 0.99, else DEFER) |
| K4112 | semantic | every single switch matches the source with that layer flipped |
| K4113 | semantic | parent OFF hides its subtree; ON restores own child states |
| K4114 | semantic | switching on a source-hidden parent shows children by their own states |
| K4106 | semantic | embedded fonts are the requested families |
| K5001 | provenance | built PDF SHA equals the build report |

Pixel comparisons: 45 dpi, a pixel matches when every channel is within ±22, a page matches at >= 0.99999 of pixels.

## Where this came from, and the DOW / gg_MATH split

Landed from the owner-private SVG-ENGINE W1 package (ZIP SHA256 `2b41da77…c5b4e`, 28/28 internal hashes
verified) and W2 package (dated 2026-11-12, all 37 internal hashes verified). Both packages stay private.
W2 already imported W1's ingress and splitter; here both live in one package and W2 imports W1 in-package.
On the original owner-private drawing this package reproduces W2's nested PDF byte for byte and its 63/63
switch result (receipt kept with the private evidence, not here).

Routing rule: engines go to DOW (this repository) unless they are math-driven, which go to `GBOGEB/gg_MATH`.

| Module | Home | Reason |
|---|---|---|
| all modules above | DOW | Format adapters, builders and QA: parsing, PDF/OOXML object models, rendering oracles |
| `ooxml_geometry.map_into_frame` | DOW | The one geometry kernel (about 15 lines). It encodes PowerPoint's frame *semantics* (an application rule, verified against PowerPoint), not general transform mathematics. gg_MATH has no 2D frame/affine kernel to import (only triangle meta-transforms), and splitting it out would add a cross-repo import for one application-specific function. Revisit if gg_MATH gains a general 2D transform kernel. |

What did **not** land here, and why: the project-specific receipt composer, the project HTML explorer upgrade,
the browser QA of that explorer, and the project-specific K-series counts. They encode one owner-private drawing
(layer IDs, labels, tags, file names) and stay with that project's private evidence.

"""SVG-ENGINE: source-faithful diagram ingress and layered redraw with provenance (DOW engine).

Modules
-------
ingress          native SVG parsing, safety validation, layer tree (W1)
paint_runs       paint-order splitter: one owner layer per contiguous paint run (W1)
pdf_ocg          layered PDF builders: nested-BDC OCGs with true parent semantics (W2), flat baseline (W1)
fidelity         redraw fidelity checks: structural, visual and semantic, against an SVG oracle (W2)
ooxml_geometry   PowerPoint frame-model group geometry and effective font chain (W2)
ooxml_inventory  OOXML structural inventory, review bridge, tag crosswalk, layer CSV reconciliation (W1)
ooxml_qa         adapter vs PowerPoint COM oracle; W1-vs-W2 regression (W2)
page_identity    authored-PDF page identity by native text tokens (W2)
fixtures         synthetic PPTX and SVG fixtures (no proprietary content)
oracles/ppt_com_oracle.ps1  PowerPoint COM oracle (Windows-only verification lane)

Heavy dependencies (lxml, PyMuPDF, CairoSVG, numpy, python-pptx) are imported by the modules that need them.
Evidence class of every output: REVIEW_ONLY; nothing here grants engineering approval.
"""

__version__ = "0.2.0"
ENGINE_WAVE = "W2"

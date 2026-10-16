# CODE PURPLE / Office style input and TestFlight

Status: DRAFT, observational and non-admitted.

No authority transfer, merge authorization, security waiver or REX acceptance.

## Purpose and ownership

Read actual DOCX, XLSX and PPTX inputs without copying their binaries into
public Git. Extract source-bound style/theme/layout observations for approved
formatting workflows.

- ABACUS owns read-only style and test telemetry producers.
- The existing `tools/qps_binary_bridge.py` owns semantic text and anchor
  normalization. The new style probe complements it, not replaces it.
- CODEX Mission Control owns orchestration display and stage-only transport.
- Pipeline automation hub owns public federation graph/method references.
- The source repository and evidence vault retain input truth and access policy.
- Real Office binaries and private bidder information remain outside Git.

## Binary and evidence policy

ABACUS QPS round-trip policy excludes committed Office binaries. The sample
files are generated externally from source code. Public Git stores only source,
tests, contracts and docs. Full input bytes remain with their authorized owner.

Derived JSON includes exact source SHA-256, source ID, format family, a stable
style fingerprint, quality state, and explicit non-authority fields. It does
not export body text, sheet names, formula text, speaker notes or source paths.

The probe rejects unsupported formats, unsafe ZIP entries, symlinks, active or
embedded content, external relationships, suspicious compression, broken XML,
missing structural parts and invalid source identifiers.

## Supported format dimensions

### DOCX

- Named paragraph and heading styles with inherited font identities.
- Explicit run font, size, color and bold/italic usage counts.
- Page size, margins and table count.
- Theme font and color scheme.

### XLSX

- Sheet index and bounded structural counts without sheet names.
- Cell style IDs, fonts, fills, number formats and alignment.
- Chart, table, merged-range and data-validation counts.
- Formula counts, conditional formatting and freeze panes.
- Workbook theme fonts/colors. Never evaluate source formulas.

### PPTX

- Slide order and canvas geometry/aspect ratio.
- Shape, text box, image, chart, table, notes and master counts.
- Explicit font face/size, colors and presentation theme.

## Read authorized input files

```bash
python -m tools.office_style_probe ./allowed.docx \
  --source-id style-docx-v1 --out ./derived/docx.json
python -m tools.office_style_probe ./allowed.xlsx \
  --source-id style-xlsx-v1 --out ./derived/xlsx.json
python -m tools.office_style_probe ./allowed.pptx \
  --source-id style-pptx-v1 --out ./derived/pptx.json
```

These commands do not mutate Office files, upload content or authorize merging.

## Generate genuine but synthetic Office examples

```bash
python tools/build_office_style_examples.py --out ./build/office-examples
```

The local generator uses python-docx, openpyxl and PptxGenJS. It creates:

- Word: a real styled one-page document with header, footer and formatted table.
- Excel: three sheets, four formula cells, one chart and one Excel table.
- PowerPoint: three editable 16:9 slides with shapes and theme/font examples.

All sample values are synthetic. Use an approved evidence vault for real source
inputs; do not commit confidential QPS artifacts.

## Test coverage and reverse testing

```bash
python -m pytest -q tests/test_office_style_probe.py \
  tests/test_mip_testflight_plan.py \
  --cov=tools.office_style_probe \
  --cov=tools.mip_testflight_plan \
  --cov-branch --cov-report=term
```

Local build proof at initial commit: 82 pytest functions passed, 18 additional
unittest subtest iterations. Both Python modules achieved 87% aggregate
statement/branch report coverage in that local run.

Negative controls cover path traversal, duplicate ZIP members, decompression
bombs, DTD/entity XML, macro/OLE/ActiveX, external OOXML relationships, missing
workbook links, invalid style IDs, missing slide geometry and source mismatch.

TestFlight is a read-only DAG/retest recommendation model. It neither starts
workers nor changes required CI, merge or A10 policies. Reuse only source-
matched evidence. Unmeasured metrics and unverified receipts remain UNKNOWN.

## Visual QA and format fidelity

Local Word page and all three slides rendered and passed visual inspection.
The PowerPoint overflow check passed. The workbook loaded with openpyxl; its
three sheets, four formulas, chart and table were structurally verified.

Formula cache recalculation was unavailable in the local artifact rendering
environment, and is not claimed. Derived style equality does not establish
pixel-identical Office output or layout completeness. Render the outputs before
any externally published release.

## Next gates

- [x] Source-only style parser, generator and negative-test suite.
- [x] Initial local testflight DAG and style coverage measurements.
- [x] Three genuine synthetic Office artifacts rendered or inspected locally.
- [ ] Exact-head native CI, style tests, formatting and coverage validation.
- [ ] Reconcile canonical owners #2033, #1877 and binary bridge #644.
- [ ] Complete independent A10, Bandit, Safety, governance and human review.
- [ ] Governed main merge, exact-main test replay and REX recurrence.

P0 admission HOLD. Neither green local tests nor draft PR status grants
repository release authority.

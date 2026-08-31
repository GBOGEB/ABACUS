# QPS Artifact Product Contract

Status: Wave B design/functionality uplift
Scope: Excel + HTML first; PPTX/PDF/Markdown inherit lineage and style controls

## Intent

The outward artifacts are products, not only rendered views of an SSOT. The design centre for this wave is therefore:

1. usable engineering interaction;
2. explicit inputs and outputs;
3. traceable scenario state;
4. recursive lineage across derived artifacts;
5. coherent visual language;
6. deterministic QA of both content and behaviour.

SSOT remains a governance anchor, but is deliberately not the primary user-facing design objective.

## Recursive build graph

Every release records a graph, not only a flat manifest.

```text
source/evidence
  -> normalized model inputs
  -> calculation/model layer
  -> workbook model
  -> workbook views + charts + controls
  -> HTML data payload
  -> HTML navigator/dashboard/scenario UI
  -> PDF/PPTX/Markdown summaries
  -> render/browser QA evidence
  -> release manifest + lineage graph
```

Each node records:
- producer step;
- direct inputs;
- direct outputs;
- source commit;
- semantic hash;
- artifact hash when binary;
- upstream lineage IDs;
- scenario/configuration ID;
- style/theme version;
- QA result IDs;
- stale/fresh state.

Recursive lineage means a changed source node can mark every transitive dependent artifact stale, while an unchanged branch remains fresh.

## Excel product requirements

### Navigation and structure

The workbook should provide:
- a landing/navigation sheet with hyperlinks to major sheets;
- grouped tab colours by function;
- visible version/build/scenario banner;
- concise sheet purpose and I/O box near the top of each major sheet;
- stable named ranges or structured tables for model interfaces;
- frozen panes and filters where tables are long;
- clear separation of inputs, calculations, outputs, evidence, scenarios and QA.

### Inputs

User-changeable cells must be visibly distinct and validated. Inputs should support:
- scenario selector;
- configuration selector;
- bidder/source selector where permitted;
- duty/runtime assumptions;
- lifecycle horizon;
- inflation/energy assumptions where applicable;
- inclusion/exclusion switches;
- confidence/uncertainty controls where supported.

Each input carries:
- name;
- units;
- evidence class;
- allowed range or enumeration;
- default value;
- source/assumption reference;
- downstream impact family.

### Outputs

Primary outputs should be decision-oriented rather than formula-oriented:
- CAPEX/OPEX/lifecycle summaries;
- scenario delta vs baseline;
- top contributors/drivers;
- uncertainty/range presentation;
- normalized comparison views;
- completeness/evidence indicators;
- rank/priority views where governed;
- explicit exclusions and unresolved assumptions.

### Interaction

Preferred workbook interactions:
- dropdown scenario/configuration controls;
- linked summary cards;
- conditional visibility or filterable tables where practical;
- scenario compare sheets;
- reset-to-baseline guidance;
- export-ready print areas;
- internal hyperlinks back to evidence or source mapping rows.

Avoid VBA unless a use case cannot be met with portable workbook features.

## HTML product requirements

HTML is a review/scenario product, not merely an index page.

### Core layout

Provide:
- persistent top navigation;
- left-side or collapsible topic navigation for deeper models;
- summary KPI/decision cards;
- scenario/configuration controls;
- synchronized tables and charts;
- evidence/lineage drawer or panel;
- visible freshness/build state;
- links to Excel/PDF/PPTX/Markdown/release metadata.

### I/O and interaction

The HTML should support, where the underlying model permits:
- load a governed scenario payload;
- change bounded scenario inputs;
- recompute or refresh derived review values client-side or via a deterministic exported payload;
- compare current scenario to baseline;
- filter/search tables;
- switch engineering/cost/lifecycle/evidence views;
- export scenario state as JSON/CSV;
- export filtered tables as CSV;
- deep-link to a topic, row, node or scenario;
- preserve URL/query-state for review handoff where safe.

Any editable HTML scenario state is non-authoritative until explicitly assimilated through the controlled roundtrip.

### Browser QA

Playwright or equivalent browser QA should test behaviour, not only presence:
- navigation works;
- scenario controls change the intended dependent views;
- reset restores baseline;
- filtering/search works;
- export payload matches visible scenario state;
- deep links resolve;
- no console errors;
- no horizontal overflow at target widths;
- charts and tables remain readable;
- stale banner appears when lineage indicates stale dependencies;
- release/build/style identifiers are visible.

## Cross-artifact lineage

A user should be able to move both directions:

```text
Excel output cell/table
  <-> semantic output ID
  <-> HTML card/chart/table
  <-> narrative/PPTX/PDF claim
  <-> source/evidence mapping
```

This crosswalk should use durable semantic IDs rather than sheet coordinates or page numbers alone.

Minimum lineage fields:
- semantic_id;
- artifact_type;
- artifact_location;
- source_ids;
- model_step_ids;
- scenario_id;
- release_id;
- qa_status;
- freshness;
- evidence_class.

## Style system

Style is functional: it should communicate hierarchy, editability, evidence strength and state.

Use a shared design vocabulary across Excel and HTML:
- typography hierarchy;
- spacing scale;
- section/card hierarchy;
- table density tiers;
- semantic states: controlled/source-supported/derived/postulated;
- status states: pass/watch/fail/deferred/stale;
- input vs calculated vs output visual treatment;
- consistent chart labeling and units;
- accessible contrast.

Do not let a palette JSON become the objective. The objective is consistent rendered behaviour and readability. Theme tokens are implementation support.

## Functional acceptance matrix

| Lane | Acceptance evidence |
| --- | --- |
| Excel navigation | hyperlinks, sheet map, tab grouping, purpose/I-O boxes |
| Excel interaction | validation/dropdowns, scenario compare, reset guidance, linked summaries |
| Excel model I/O | named/structured interfaces, units, evidence class, downstream mapping |
| HTML navigation | topic navigation, deep links, artifact links |
| HTML interaction | scenario controls, filters, compare, exports, reset |
| HTML rendering | responsive/readable charts/tables, no overflow/console errors |
| Lineage | semantic IDs, direct + recursive dependencies, stale propagation |
| Style | shared hierarchy/state semantics with rendered QA |
| Crosswalk | Excel <-> HTML <-> narrative/deck/pdf <-> evidence |
| Release | build IDs, hashes, QA receipts, reproducible state |

## DMAIC use

### Define
Identify the user decision and interaction needed, not only the file to generate.

### Measure
Measure functional coverage:
- percentage of major workbook sheets with purpose/I-O blocks;
- percentage of user inputs validated and classified;
- percentage of decision outputs with semantic IDs;
- percentage of HTML controls covered by browser tests;
- percentage of outward claims cross-linked to semantic IDs;
- stale-dependency detection coverage;
- visual/render QA pass rate.

### Analyse
Use PCA only as a non-credit-bearing prioritization aid across product weaknesses such as:
- navigation debt;
- interaction debt;
- lineage gaps;
- rendering/style inconsistency;
- scenario I/O incompleteness;
- browser-test coverage;
- stale propagation gaps.

### Improve
Prefer changes that improve actual user interaction and traceability over adding more metadata.

### Control
Require repeatable functional tests, recursive lineage checks and stable visual QA across successive releases.

## BT priority for this product wave

1. broken or missing decision interaction;
2. missing scenario I/O / compare / export;
3. broken recursive lineage or stale propagation;
4. cross-artifact semantic crosswalk gaps;
5. readability/style defects affecting use;
6. metadata-only enhancements.

## Credit boundary

This product-functionality work improves tooling, reviewability and release quality only. It does not by itself grant DOW/KEB/PCA/BT/Table-10/Safety/compliance/engineering maturity or project-completion credit.

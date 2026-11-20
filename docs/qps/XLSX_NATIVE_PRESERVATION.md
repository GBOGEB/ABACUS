# XLSX native feature preservation

The binary bridge now includes worksheet filter trees, scoped defined names,
sheet visibility, hidden rows and columns, and explicit calculation settings in
its XLSX semantic identity. A workbook with unchanged cell text and a changed
filter criterion is a different semantic input. Parser version 1.2.0 identifies
the expanded fingerprint. Rebuild derived fingerprints when changing from 1.1.0.

The bridge retains its existing cell-value interpretation and shared-string
fallback. Its feature-only read retains raw shared indices and captures formula
attributes. Preservation and repair snapshots resolve shared strings and reject
invalid references by default.

## Owned-engine repair evaluation

`tools/qps_xlsx_native_features.py` extends the existing openpyxl engine used by
`scripts/build_qps_ssot_views.py`. The builder exposes
`evaluate_native_feature_repair(...)`; the QA engine exposes
`check_source_native_preservation(...)`. Existing JSON-to-review-view generation
continues to use its established layout and does not import source authority.

The repair evaluator accepts a source and a previously authored candidate, each
bound to an expected SHA-256. It restores supported features in a disposable
openpyxl model, serializes to memory, and checks the resulting bytes using an
independent OOXML reader. It produces a receipt only. It never writes a repaired
workbook or edits either input.

```bash
python tools/qps_xlsx_native_features.py \
  --source /private/source.xlsx \
  --candidate /private/candidate.xlsx \
  --expected-source-sha SOURCE_SHA256 \
  --expected-candidate-sha CANDIDATE_SHA256 \
  --receipt /private/repair-evaluation.json
```

The receipt path must not already exist and must not resolve to either input.
Exit status 3 means the serialized trial still loses required information.
Wrong hashes, reordered sheets, unsupported filter extensions and malformed
scoped identities fail before any output workbook can be produced.

## Supported restoration and independent checks

- Worksheet AutoFilters and active criteria use `AutoFilter.from_tree` and
  `Worksheet.auto_filter`. The serialized check compares the complete behavior
  tree, including each criterion.
- Sheet visibility uses `Worksheet.sheet_state`. The serialized check compares
  source visibility for every sheet.
- Explicit calculation settings use `Workbook.calculation` and `CalcProperties`.
  Every source-explicit setting must remain explicit after serialization.
- Scoped filter names use writer-generated names for filters and
  `Worksheet.defined_names.add` for orphan names. The check compares scope,
  name, hidden flag and formula text.
- Print areas and titles use `Worksheet.print_area`, `print_title_rows` and
  `print_title_cols`. Scoped names and ranges must remain verbatim.
- Existing values, formula text, formula attributes and caches remain in the
  candidate model. The check compares all candidate and serialized-trial cells.
- Existing hidden rows and columns remain in the candidate model. Their sets
  must match the source exactly.

Do not manufacture an AutoFilter for a source sheet that only has a scoped
filter name. Do not add a second reserved name when the writer generates one.
Duplicate name-plus-scope keys are rejected by the reader rather than collapsed.

The native comparison is intentionally strict. Equivalent quoting of a sheet
name can still fail a verbatim source contract. Such a difference may be
classified by a reviewer, but the evaluator does not silently relax the rule.
Likewise, missing formula caches are losses even when formula text is retained.
The evaluator never fabricates a cache or relabels a stale result as
recalculated.

## Acceptance boundaries

`REJECTED_SERIALIZED_LOSS` is a failed preservation trial. The receipt contains
all remaining native and content differences, and `output_workbook_written` is
false. `PRESERVATION_PASS_NATIVE_RUNTIME_UNQUALIFIED` proves only the specified
serialized preservation checks. It does not establish calculation correctness,
filter execution, rendering quality, Excel's repair-free opening, contractual
acceptance or stakeholder disposition.

Openpyxl can configure filters but does not apply them, and it is not a formula
calculation engine. Native Excel or another explicitly qualified calculation
engine must prove filter-aware results on the final bytes. The artifact-tool
authoring route remains a separate capability; this implementation does not
patch that managed package or substitute an unqualified output for its result.

References: [openpyxl filters][filters], [defined names][names], and
[filter API][api].

[filters]: https://openpyxl.readthedocs.io/en/stable/filters.html
[names]: https://openpyxl.readthedocs.io/en/stable/defined_names.html
[api]:
  https://openpyxl.readthedocs.io/en/stable/api/openpyxl.worksheet.filters.html

## Verification

```bash
python -m pytest tests/test_qps_binary_bridge.py \
  tests/test_qps_xlsx_native_features.py
```

The new tests also run with `python -m unittest discover -s tests -p
test_qps_xlsx_native_features.py`. Fixtures are generic and contain no project
evidence. They cover equal-count criterion changes, scope and visibility,
explicit-false settings, hidden rows/columns, lost formula caches, wrong hashes,
malformed XML declarations and preservation of both input byte streams.

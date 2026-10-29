# Changelog — MYRRHA WCS Handover

All notable changes to the MYRRHA Warm Compressor Station engineering handover package.

## [0.5.0] — 2026-10-26

### Added
- `master/icd_inputs.yaml` — read-only projection of the controlled SSOT (cryoplant-project) electrical/thermal anchors
- `master/compute_utilities.py` — ICD-bound utility engine (electricity → recoverable water heat → cooling-water flow → HVAC residual)
- `master/validate_consistency.py` — parity gate: fails on isothermal-basis electricity, conflated HP+B flows, or 350 g/s shown as design anchor without a legacy label
- `icd-electrical.html` — new view presenting the ICD-bound chain, 3-of-4 vs 4-of-4 at the 326 g/s anchor, flow→power scaling, and open items (EL-R04, CC envelope, PVPS running count, CC CW per-branch)
- `icd_bound_utilities` block in `master/data.json`

### Changed
- Electricity is now **consumed from the ICD** (Kaeser 357 kW/unit at design; PVPS 18.5 kW/unit), not derived from isothermal work ÷ efficiency
- HP flow and B flow are treated as **separate drivers** (binding rule of QPS_WCS_HP_PVPS_THERMO_CONTROL_ICD_W52); they are no longer summed into one sizing flow
- Design anchor aligned to the ICD nominal 2K OP of **326 g/s HP total** (350 g/s retained only as a legacy/utility figure)
- Old PVPS `utilities` isothermal/fraction keys marked DEPRECATED (retained, not deleted)
- Live chrome version badge → v0.5.0

### Notes
- The private SSOT was NOT modified; open items are carried forward, not resolved
- 350 g/s on 3 HP units is infeasible (75 Hz > 72 Hz cap); it requires 4 units

## [0.4.7] — 2026-05-20

### Added
- MT-11 Kaeser technical requirements view
- MT-12 PVPs technical requirements view
- MT-13 comprehensive report with execution summary
- Accessibility audit report (WCAG 2.1 AA)
- Mobile responsiveness fixes and changelog
- Responsive design review page
- QA test suite with automated checks

### Changed
- British English enforced throughout all 46 views
- Mobile-optimised layout across all pages
- Updated vendor-kaeser comparison tables

### Fixed
- Action tracker interactive filters
- Status page progress calculations
- Cross-reference links between views

## [0.4.1] — 2026-05-13

### Added
- Bayesian truth ranking, scatter, validation, and artefact views
- DMAIC review and statistical analysis pages
- Interaction analysis and testing strategy views
- Code quality dashboard
- Weighted priority matrix
- Search index page
- Artefact index and tracker

### Changed
- Expanded navigation across all pages
- Enhanced QA checklist

## [0.3.0] — 2026-05-10

### Added
- Core HTML ecosystem: index, slides, reports, tables, graphs, status, truth, utilities
- Vendor Kaeser comparison page
- Heat exchanger sizing calculator
- Thermodynamic analysis view
- Operations overview
- Slide editor with live preview
- Master config, data, and render pipeline
- Design guide, editing guide, slide notes documentation
- Light/dark theme with font selector
- CSV/JSON export for all tables

## [0.1.0] — 2026-05-09

### Added
- Initial markdown comparison note (MYRRHA warm-compressor comparison A.md)
- Data extraction from ALaT and LKT pre-studies

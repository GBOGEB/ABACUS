# 21-Point Integration Progress Tracker

| # | Work element | Status | Owner / helper | Notes |
|---:|---|---|---|---|
| 1 | Clear Applicant answer structure | started | assistant | Drafted in session; needs final consolidation. |
| 2 | Reduced model boundary | complete | assistant | Boundary defined around QCELL/QVE -> Line S -> recovery compressors -> HP path. |
| 3 | Source register from D2.1 | complete | assistant | `source_register.md` exists. |
| 4 | RTM traceability table | started | Agent A | Issue #583 created. |
| 5 | Scenario matrix | started | Agent A | Issue #583 created. |
| 6 | Pressure-build-up formula set | complete | assistant | Ideal-gas formula in README and Python model. |
| 7 | 100 / 112 / 150 / 200 g/s sensitivity | complete | assistant | Included in README and Excel artifact. |
| 8 | HP compressor start-delay sensitivity | started | assistant | Spreadsheet includes pressure rates; detailed delay table pending. |
| 9 | Volume sensitivity | not_started | Agent B | To add scenario data and runner. |
| 10 | Temperature sensitivity | not_started | Agent B | To add scenario data and runner. |
| 11 | Initial-condition sensitivity | started | assistant | D2.1 baseline and 1.2 bar case identified. |
| 12 | Appendix 8.2 topology extraction | started | Agent A | PFD topology identified; detailed extraction pending. |
| 13 | Appendix 8.3 model block map | started | assistant | Three-block SIMCRYOGENICS lineage captured. |
| 14 | Appendix 8.4 mode/valve extraction plan | started | Agent A | Valve-state extraction pending. |
| 15 | Excel block structure | complete | assistant | XLSX generated in session; repo integration pending. |
| 16 | Python block structure | started | Agent B | `line_s_buffer.py` exists; issue #584 created. |
| 17 | CoolProp upgrade path | started | Agent B | Hook only; not implemented. |
| 18 | ABACUS repo scaffold plan | complete | assistant | PR #582 active. |
| 19 | CODEX reusable tooling plan | started | CODEX helper | Issue #237 created. |
| 20 | PR text / branch plan | complete | assistant | Branch `w001`, PR #582. |
| 21 | Open issue / confirmation list | started | assistant | Needs formal open-items register. |

## Current completion view

- Complete: 7 / 21
- Started: 12 / 21
- Not started: 2 / 21
- Blocked: 0 / 21

## Front-heavy execution rule

Prioritize source register, scenario matrix, RTM traceability, index, glossary, and validation scaffold before expanding into full SIMCRYOGENICS reproduction.

# CODE PURPLE - acceptance debt (read-only projection)

**Evidence checks are NOT admission approval.** A checked observation means
a source-bound receipt was recorded under the frozen comparison context.
The native runner, security owner and independent reviewer must still
reconfirm current exact-head evidence; `main` admission remains **HOLD**.

| ID | Evidence | Admission | Repository | Acceptance item | State |
| --- | --- | --- | --- | --- | --- |
| CP-A009 | [ ] | [ ] | GBOGEB/ABACUS | Independent A10 and owner-reviewed disposition | MISSING |
| CP-C003 | [x] | [ ] | GBOGEB/ABACUS | Current exact-head 546/546 four-module testflight | OBSERVED |
| CP-D006 | [ ] | [ ] | GBOGEB/ABACUS | Markdown/YAML/JSON lint on exact head | MISSING |
| CP-F005 | [ ] | [ ] | GBOGEB/ABACUS | Black and isort formatter verified clean on exact head | BLOCKED |
| CP-G004 | [ ] | [ ] | GBOGEB/ABACUS | Fresh native 253-run graph at current source head | STALE |
| CP-H001 | [x] | [ ] | GBOGEB/ABACUS | Historical 253/253 native run readback, 492 jobs, 67 signatures | OBSERVED |
| CP-H002 | [x] | [ ] | GBOGEB/ABACUS | Historical CBD module branch coverage and 191/191 proof | OBSERVED |
| CP-M010 | [ ] | [ ] | GBOGEB/ABACUS | First correctly admitted protected-main merge and REX | MISSING |
| CP-S007 | [ ] | [ ] | GBOGEB/ABACUS | Independent Safety/Bandit P0/P1 security gate | MISSING |
| CP-V008 | [ ] | [ ] | GBOGEB/ABACUS | Workflow inventory classified and governance terminal | MISSING |
| CX-E011 | [ ] | [ ] | GBOGEB/CODEX | Authenticated Mission Control disjoint Crew execution | MISSING |
| CX-R012 | [ ] | [ ] | GBOGEB/CODEX | CODEX independently source-bound REX and review return | MISSING |
| QP-E013 | [ ] | [ ] | GBOGEB/cryoplant-project | QPS independent engineering acceptance and provenance | MISSING |
| QP-F014 | [ ] | [ ] | GBOGEB/cryoplant-project | QPS federation reverse smoke and evidence consumer | MISSING |

## Evidence links (source-bound observation only)

- CP-C003: [read native source](https://github.com/GBOGEB/ABACUS/actions/runs/39023241727/artifacts/12097169116) on head `2f42d6da76a447a40e9ae2f7a72f960aa73c8623`; status `OBSERVED`.
- CP-F005: [read native source](https://github.com/GBOGEB/ABACUS/actions/runs/39023241727/artifacts/12097204196) on head `2f42d6da76a447a40e9ae2f7a72f960aa73c8623`; status `BLOCKED`.
- CP-G004: [read native source](https://github.com/GBOGEB/ABACUS/actions/runs/39021567900/artifacts/12096926766) on head `068ca4a7d1f8a74e3f8e0ef28c388f5a6ca8b52b`; status `STALE`.
- CP-H001: [read native source](https://github.com/GBOGEB/ABACUS/actions/runs/39021567900/artifacts/12096926766) on head `068ca4a7d1f8a74e3f8e0ef28c388f5a6ca8b52b`; status `OBSERVED`.
- CP-H002: [read native source](https://github.com/GBOGEB/ABACUS/actions/runs/39021567900/artifacts/12096846922) on head `068ca4a7d1f8a74e3f8e0ef28c388f5a6ca8b52b`; status `OBSERVED`.

Unknown values are `null`, not zero. Root closure,
Crew dispatch, current-main and diff coverage are unverified.

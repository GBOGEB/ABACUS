# CODE PURPLE W78 — Source-lease safety and coverage convergence

**Evidence class:** source implementation candidate; not an admission, executed
Crew launch, owner authorization, or canonical root closure.

## Problem and design decision

The existing W33 elastic-wave governor accepted only duplicate *literal*
paths as a conflict. Nested directories and files, or Windows case aliases,
could be proposed as independent source-owner work. The G3G graph contract
recognized prefix overlap but treated repository names and paths as
case-sensitive and accepted ambiguous path bytes.

W78 preserves both established entry points. Neither becomes a scheduler:
`elastic_wave_governor.evaluate` proposes bounded capacity and
`g3g_disjoint_crew.assess` validates source leases and a read-only DAG.
Changes are **fail-closed lexical checks**, not realpath, symlink, ACL,
authentication, or GitHub branch-protection proof.

## Two disjoint source-owner lanes

| Lease | Existing SUT | Native test file | Responsibility |
| --- | --- | --- | --- |
| W78-A | Governor | Native tests | Cross-family leases; bounded capacity |
| W78-B | G3G | Native tests | Repo-aware DAG leases; no worker authority |
| W78-TEST | W29 | Native Testflight | Shared integration reader only |

The two module/test pairs are disjoint. The shared native Testflight is
serialized per PR and MUST not be counted as two independent executed Crew
workers. Existing W76/W77 zero-covered source owners retain their own paths;
existing Dockerfile PR #2361 remains outside this source scope.

Source files: `MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/elastic_wave_governor.py`
and `MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/g3g_disjoint_crew.py`.
Their tests are `test_elastic_wave_governor.py` and
`ci/governance/tests/test_g3g_disjoint_crew.py`.

## SIPOC

| Stage | Contract |
| --- | --- |
| Supplier | GitHub exact-source checkout; MIP controller and G3G proposals |
| Input | Typed IDs, relative paths, exact SHA and source-bound receipts |
| Process | Validate paths and leases; evaluate DAG and stop policy |
| Output | Fail-closed proposal; hashed JUnit, coverage and manifest |
| Customer | Admission, canonical BD and orchestration owners |

No delegated write authority is granted.

## Dependency DAG

~~~mermaid
flowchart TD
  A["01 Exact source SHA"] --> B["02 Safe lexical lease"]
  B --> C{"03 Nested/case alias or traversal?"}
  C -->|yes| H["HOLD: unsafe owner collision"]
  C -->|no| D["04 G3G typed acyclic DAG"]
  D --> E["05 Existing W29 Python 3.10/3.12"]
  E --> F{"06 Native jobs terminal and tests green?"}
  F -->|no| H
  F -->|yes| G["07 Source-hashed JUnit + line/branch denominators"]
  G --> I{"08 Independent governance + security + review?"}
  I -->|no or unknown| H
  I -->|yes| J["Owner-controlled admission, separately evidenced"]
~~~

## SPLINE / wave acceptance

`N0 snapshot SHA -> N1 two source leases -> N2 nested/case/traversal
negative and reverse mutation tests -> N3 positive sibling/different-repo
controls -> N4 two native OS/Python jobs -> N5 same-source-file
statement+branch numerators/denominators and ZIP hashes -> N6
governance/Safety/Bandit/CodeQL -> N7 independent eligible review ->
N8 owner disposition`.

**Stop** on source-head movement, symlink/realpath ambiguity, missing native
job/attempt, JUnit disagreement, skipped/failing test, invalid denominator,
a zero-covered leased module, or missing required control. Coverage of the
six-source W29 scope is not ABACUS main coverage.

W78 targets **both assurance modules at nonzero line and branch coverage**;
80% per module is the next review threshold, 100% only for reachable and
measured behavioral paths. A pre-W78 four-source W29 run cannot be used as
a matched six-source baseline. New 6-file instrumentation widens scope;
a zero-to-positive credit requires independently comparable receipts for the
*same source/blob/config/eligible denominator*, not merely a larger test count.

### Reverse/adversarial matrix

- `a` vs `a/b.py` and `A/B.py` vs `a/b.py`: reject.
- `a/file.py` vs `a/file.py-old`: permit (segment boundary).
- Traversal, duplicate separators, backslashes, alternate streams, absolute
  paths, control bytes and trailing dots/spaces: reject.
- Same path in distinct **actual** repositories: allow. Case aliases of one
  GitHub repository: reject.
- A → malicious B → original A: preserve the original result without mutation.
- Missing owners, reviewers, runners, security proof or current source: no
  admission/dispatch credit.

## Telemetry and administrative boundaries

Receipt keys: exact `source_sha`, `run_id`, `run_attempt`,
`job_label`, six scoped filenames with source SHA-256,
per-module `covered_lines/eligible_statements` and
`covered_branches/eligible_branches`, JUnit element and header totals,
failure and skip counts, and hashed JUnit/coverage artifacts.

The programme still requires effective GitHub required checks,
last-push approvals, resolved discussions, independent human/security review,
and a blocked RED canary. Existing bypass grants are not waived here.
`MERGE_ADMISSION=HOLD`, `authority_transfer=false`,
`security_waiver=false`, `14_PACKAGE_CLOSURE=UNVERIFIED`.

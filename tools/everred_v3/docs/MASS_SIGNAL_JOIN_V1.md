# CODE PURPLE — Mass-signal disjoint scanner census v1

**Owner:** ABACUS / EVERRED CENSUS. **Outputs:** read-only causal
*proposals*, not verified roots, security waivers, runtime proof or QPS acceptance.

## Exact-source native Flake8 pulse (16 October 2026)

- Repository: `GBOGEB/ABACUS`
- Exact SHA: `bdbb8c21d6de2ef270f7fe0eedbeadf2fa200036`
- Native workflow: DAB Flake8 Census, run `38870931116`, attempt `1`;
  job `116874572746`; original artifact `12032899404`.
- Original ZIP SHA-256:
  `2e9c104357075fbf55e5f8cf6f1f519f6303b23bc72996536d6dedb6ef375609`
- Native census reports **3,595** Flake8 occurrences; 34 rule families;
  count sum is 3,595; **1,065 DAB work proposals**.
- Major families: E501 1,037, E402 650, E231 410, F401 339,
  F541 270. Remaining rule families sum to 889.
- G1: OPEN, count threshold strictly less than 3,000, companion proof
  required; G2 (<2,500) and G3 (<2,000) are also OPEN.
- Scan command uses `--exit-zero`. A green census is **not** a passing
  enforced format/security ratchet.
- The earlier 2,983-finding handover is not source/config matched to
  this run. Difference +612 is not an accepted trend or regression.

## First implementation slice: scanner join

`src/mass_signal_join.py` consumes explicitly source-bound
`abacus.everred.mass-signals.input.v1` JSON containing:
repository, exact SHA, native run/attempt/job, original artifact digest,
scanner configuration digest, collection mode and enforcement semantics.
Accepted detectors: Bandit, Flake8, Ruff, Semgrep, CodeQL and Black.

- Aggregate-only producer counts may contribute rule totals **only**.
  They provide no path/line identity and earn no source-level roots.
- Detailed scanner occurrences produce stable fingerprint candidates.
  Cross-scanner grouping requires the **same repository, SHA, path,
  line and conservatively recognized rule family**.
- A shared fingerprint is a `UNCONFIRMED_CAUSAL_CANDIDATE`;
  true causal ownership, repair, recurrence and root closure require
  independent native proof.
- A scanner-level label `blocking` is not merge admission.
  Explicit `continue_on_error` and workflow conclusion are retained,
  required check is separately observed or UNKNOWN.
- No unknown population converts to zero; no historical scanner count
  is injected into a new live exact-head report.
- The negative suite includes source drift, count mismatch, duplicate
  evidence, rule/path traversal, waived enforcement inference and
  unsupported QPS authority.

Run from `tools/everred_v3`:

~~~sh
python -m unittest discover -s tests -p test_mass_signal_join.py -v
python src/mass_signal_join.py --input cohort.json --output out/census.json
~~~

The producer is **not** authorized to call remote GitHub APIs or mutate
any code. Authentic artifact bytes must be supplied and checked by the
repository owner before generating a native census.

## Next root-ranked expansion and consumer proof

| Domain | Next producer/consumer | Expected evidence |
|---|---|---|
| Semgrep | Stable SARIF to normalized detailed occurrences | rule, sink, path, line, artifact SHA and enforcement |
| Ruff | S607/S314/S110/S112 correlated with Bandit/Semgrep | candidate groups, not closed roots |
| Flake8 | Existing DAB queue per disjoint owner | before/after same scope, G1 budget and ratchet |
| Black | historical repo 741/889 vs bounded EVERRED 22/41 | separate base debt and changed-file mutation |
| RHEL/UBI | authenticated container/host source | OS/image/arch/FIPS cells and actual runtime receipts |
| Docker | cold/warm/negative image and port matrix | daemon, image digest, container and health proofs |
| LLDB/LDAB | true debugger session and joined BD root | breakpoint/step/build ID/session bound to run/job |
| YAML/JSON/TOML | false-schema, duplicate-ID and DAG corpus | fail-closed control-plane proof |
| Logging | S110/S112 and redaction/exception lineage | observed exceptions, hash, truncation and root owner |
| OSV | installed/identified/unscannable package denominator | new-vulnerability delta and scan semantics |

**Global DoV** remains an owner-usable QPS engineering deliverable,
accepted decision or externally usable release, not a reduced scanner
count. Static COLD analysis does not grant runtime acceptance.

**Admission:** independent A10 and Safety required; merge HOLD,
new four-hop federation UNKNOWN, QPS DEFER, formal credit delta zero.

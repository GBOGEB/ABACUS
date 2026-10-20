# CODE PURPLE / GoGREEN / EVERRED: Acceptance Debt, P1-P3

**Status:** offline-tested implementation candidate. **Main admission: HOLD.**
**Human checks and machine checks are separate**, and a valid event is not an
independent security review, a verified causal-root closure, or proof of merge.

## Governance and ownership

| Plane | Canonical scope | Consumer responsibility |
| --- | --- | --- |
| ABACUS | #1929 evidence; #1860 admission | Read-only BD projection |
| CODEX | #977 Mission Control | Governance consumer |
| QPS | Engineering acceptance | Source lineage consumer |

The implementation is path-disjoint and should be proposed to ABACUS from a
separate branch. No direct commit to protected `main`. A compliant pipeline
shall later re-run exact-head native checks, effective policy and independent
review prior to admitting changes to main.

## The five evidence invariants

1. Each requirement has immutable ID, owning repository, human title, scope,
   prerequisites, and explicit kind (security, review, test, etc.).
2. Each observation binds `repo`, `ref`, **40-hex source head SHA**, exact base
   and policy SHA, **monotone head epoch**, native source URL and SHA-256.
   The epoch prevents A -> B -> A from inheriting stale approvals.
3. The ledger is append-only by contributor path; repeated identical event IDs
   are aliases, conflicting IDs fail, and a newer FAIL supersedes old PASS.
4. `evidence_checked` means the observation is structurally recorded under the
   frozen comparison context. It **does not** mean the provider is independently
   authenticated. `admission_checked=false` until separate canonical authority
   provides real attestation; this implementation never authorizes a merge.
5. `UNKNOWN` is JSON `null`, not numeric zero. Module coverage is never copied
   into repository-main coverage. Cross-repo edges are dependencies, not
   authority transfers or accepted causal roots.

## Git and fan-out implementation

Make three sequential, path-disjoint **commits** on one source-owner branch,
then publish the branch *once* to avoid obsolete-head CI fanout:

- **P1 Define / contract:** `acceptance/core.py`, contract, exact-repo contexts,
  fail-closed negative tests and source-bound path-lease rules.
- **P2 Measure / graph:** `acceptance/graph.py`, frozen contributors,
  typed nodes/edges, blocker-reach computation, SIPOC/consumer requests and
  reverse-dependency tests.
- **P3 Analyze / Improve / Control:** `acceptance/telemetry.py`, `render.py`,
  `cli.py`, CLI tests, deterministic SHA manifest, HTML review/dashboard,
  three-wave transition telemetry and pre-registered N+2 forecast score.

Disjointness applies to **changed files and their canonical source owner**;
reader workers can split by run ID. CODEX/QPS reader adoption should be
submitted in separately owned PRs after the ABACUS contract stabilizes. No
code is pushed to those repos by this ABACUS provider candidate.

## DMAIC and local MIP loop

Local MIP label is **Measure -> Improve -> Prove**. It is a local engineering
convention, not an authenticated Mission Control dispatch.

| Local wave | Executed tests | Statement + branch target | Evidence |
| --- | ---: | --- | --- |
| P1 contract | 16 | Core 99% | First-red fixture repaired |
| P2 graph | 29 | Core + graph 99% | DAG and lease tests |
| P3 control | 56 | **500/500 = 100%** | CLI, reverse, XSS, hashes |

Percentages across P1/P2/P3 use **different source denominators** as modules
were added; do not describe them as same-scope coverage percentage-point gains.
The final 500/500 is from a local Python coverage.py run and must be
repeated in native GitHub Actions on a new exact PR head.

A local three-pulse replay of immutable prior native observations from #2091
and #2101 yields evidence-checked 1/14 -> 2/14 -> 3/14, with 2 status
transitions in each later pulse and 85.7% state retention. The final snapshot
also has 1 stale, 1 blocked and 9 missing obligations. This is **not three
independent remote trials**: no formal CI, PCA convergence claim, or causal
inference is warranted.

The evidence graph contains **25 nodes and 38 typed edges**, including 16
prerequisite edges and three cross-repo edges; these are not verified causal
root equivalences. Predicted P3 at the end of P2: >=40 passing tests, >=90%
package coverage and zero unauthorized admissions. P3 observation: 56 tests,
100% and zero unauthorized admissions. This was a pre-registered design target,
not a statistically calibrated forecast.

## SIPOC

| SIPOC | Source-bound process |
| --- | --- |
| S | GitHub artifacts; ABACUS #1929; CODEX and QPS owners |
| I | Repo, head/base/policy/epoch, run URL and hash |
| P | P1 contract -> P2 DAG -> P3 tests and review |
| O | Acceptance JSON, HTML, DAG, SIPOC, SHA receipts |
| C | ABACUS BD, CODEX, QPS, independent reviewer |

### Reverse testing and actual first-red lessons

- Bad source/repo, missing denominators, duplicate IDs, forged admission and
  attacker URLs fail closed.
- A -> B -> A previous-generation evidence is marked STALE even if head SHA
  returns to its former value.
- An observed green followed by a newer red is BLOCKED, not inherited PASS.
- A historical 253-run receipt is allowed as a historical observation; it does
  not certify a new PR's 253-run scout. Old-head graph proof stays STALE.
- Dependent rollup failures have unconfirmed causal-root identity; graph reach
  is a deterministic structural upper bound, not an estimated fix success.

## Re-run locally

```bash
cd tools/everred_v3
python -m unittest discover -s tests -p 'test_acceptance_*.py' -q
python -m coverage run --branch --source=acceptance \
  -m unittest discover -s tests -p 'test_acceptance_*.py' -q
python -m coverage json -o /tmp/acceptance-coverage.json
python -m acceptance.cli \
  --contract acceptance/input/obligations.json \
  --contexts acceptance/input/contexts.json \
  --events acceptance/input/observations.jsonl \
  --out /tmp/cbd-acceptance
```

A `read-only` build does not query GitHub live. Source snapshots are frozen; an
independent native exporter is required to provide fresh observed events and
safely update comparison contexts, including head-generation epoch and policy.
No reverse dispatch, automatic refresh of main, or canonical accepted ledger
write has been implemented.

## Admission obligations (deliberately unresolved)

- [ ] Native exact-head tests and same-source coverage for the new PR
- [ ] Independent native API authentication of stored observation digests
- [ ] CODEX/QPS source-owner consumer integration and reviewer disposition
- [ ] Security, Bandit/Safety, governance and A10 independently green
- [ ] Effective protected-main readback and qualified broad/diff coverage
- [ ] First correctly admitted PR merge and exact-main REX verification

Existing known debt and unrelated workflow reds are carried forward; no
security waiver, path lease release, implicit merge or root closure claimed.

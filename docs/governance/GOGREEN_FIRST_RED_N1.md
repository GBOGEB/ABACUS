# GoGREEN N+1: first-red linkage, root candidates and coverage proof

Status: source-owner testflight; evidence only, no merge admission.

## Reuse, ownership and actual inputs

This is a disjoint extension to `scripts/gogreen_root_leverage.py` and the
existing EVERRED `tools/everred_v3/scripts/cbd_260.py` census. It is not a
replacement root registry, new Mission Control planner or new GH Actions gate.

The `tools/everred_v3/data/cbd_260/N0_*.json` frozen cohort owns the **260
failed workflow associations / 253 distinct failed run IDs** denominator.
GoGREEN consumes explicit native job/step evidence from bounded source-pinned
readbacks; output only retains candidate signatures and source-linked evidence.

The included `tests/fixtures/gogreen_n1_native_first_red_sample.json` contains
12 actual GitHub first-red job observations from 10 distinct runs across six
PR heads, with verified run-attempt identities and native run URLs. No source
log bodies, tokens, corporate Office binaries or private engineering content.

The sample has six *signature candidate* buckets (not root identities):

- Governance `policy-and-inventory` — three PRs
- Python 3.10 matrix install — two PRs
- v032 canonical dependency installation — two PRs
- Code-quality new-debt ratchet — two PRs
- Bandit new-debt ratchet — two PRs
- Changed-document validation — one PR

The two Python 3.10 cohorts independently show the Matplotlib resolver
incompatibility in job logs; source owner #2026 holds that dependency repair.
Governance repair belongs to #1995/#2041; Bandit/Safety belongs to #1738,
#2027 and the independent security owner. Other failures are not collapsed.

## Execute locally or on an authorized exact-head runner

```bash
python -m unittest discover -s tests -p 'test_gogreen_first_red_wave.py' -v
python scripts/gogreen_first_red_wave.py \
  tests/fixtures/gogreen_n1_native_first_red_sample.json \
  --output /tmp/gogreen-first-red-n1.json
python -m coverage run --branch -m unittest discover -s tests \
  -p 'test_gogreen_first_red_wave.py'
python -m coverage report -m scripts/gogreen_first_red_wave.py
```

The local new-module test group initially passed 25 unittest methods; its
reported statement+branch coverage is 98% on this module only. Its exact
native head is not accepted until CI produces an attributable run receipt.
Main, diff and full estate coverage remain UNKNOWN without comparable proof.

## N+1 / N+2 / N+3 work admission

| Wave | Input | Output / observable success |
| --- | --- | --- |
| N+1 | Native first failed job/step | Exact-head matrix, no fabricated roots |
| N+2 | Owner-accepted roots | Source fix and before/after CI |
| N+3 | Required admission gates | Main replay, regression/REX proof |

Group common observed signatures for *investigation*. Only a dispositioned
root ID with independent owner evidence may count as a causal root. An
aggregate `Full Red Proof Summary` or proof-completeness cascade is not a
separate accepted root by default.

Bounded output proposals allow at most four **read-only** scouts. Source
writers require a distinct owner path lease, approval and exact head; this
module grants zero write workers and never invokes GitHub dispatch.

## Coverage and test-depth admission rule

Coverage receipts must bind exact PR SHA, tool version, selected tests, module
fingerprint, statement/branch numerators and denominators, and changed-line
counts. A before/after percentage-point delta exists only for matched tool,
configuration, test selection and unchanged covered population. Unmatched
cohorts are `INCOMPARABLE`, not zero gain and not a failed test.

Adversarial tests include stale/short source SHA, forged accepted owner roots,
duplicate/conflicting native jobs, cross-head attempts, wrong GitHub URLs,
security/admission booleans, skipped-vs-failed confusion, branch mode,
numerator inflation, alias duplicate accounting, downstream aggregate steps,
deterministic output and no unapproved crew launch.

## Existing control dependencies

- ABACUS #1929: sole root/LDAB evidence contract and root disposition.
- ABACUS #1877 and #2033: CI reuse, job/queue telemetry and gate domains.
- ABACUS #1860 and CODEX #977: admission and crew authorization HOLD.
- ABACUS #2077: historical workflow-to-native first-red census producer.
- ABACUS #2080: this root-leverage source owner and candidate telemetry.
- GoGREEN hub: read-only REX and positive-evidence consumer.

Do not interpret testflight fixture success as main coverage improvement, a
security waiver, worker launch, root closure or an admitted merge.
`authority_transfer=false`, `merge_authorized=false`, `security_waiver=false`.

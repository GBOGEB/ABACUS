# DOW repo-deep handoff — QPS / TRIAGE chat-to-GitHub bridge

Status: implementation candidate
Date: 2026-09-11
Repository: `GBOGEB/ABACUS`
Role: runtime challenge, orchestration, census/metrics projection, exact-receipt consumption.
Authority ceiling: ABACUS cannot mutate QPS engineering, compliance, negotiation or release truth.

## 1. Reused current ABACUS surfaces

This lane extends current DOW/federation controls rather than creating a parallel orchestration stack.

- `governance/federation/FEDERATION_ACTIVITY.yaml` — current federation activity projection.
- `governance/qps_triage/DOW_CONTRACT_v1.json` — machine-readable DOW consumer/challenge contract added by this wave.
- `tests/test_qps_triage_dow_contract.py` — fail-closed contract regression test.
- Recent DOW precedents: #1096 floating DOW census; #1102 consumer contract; #1105 W107 roll-up; #1107 exact KEB receipt ACCEPT.

## 2. DOW object boundary

ABACUS consumes exact producer identity and receipt evidence from KEB or an explicitly scoped child challenge contract. It may measure, challenge, render or orchestrate, but it never becomes child engineering authority.

```text
DOW_RECEIPT_CONSUMER
DOW_RUNTIME_CHALLENGE
DOW_METRIC_PROJECTION
DOW_CENSUS
DOW_ORCHESTRATION_RESULT
DOW_ACCEPT_REJECT_DEFER_RECEIPT
DOW_DEFERRED_EVIDENCE_GAP
```

## 3. Repo-deep pickup sequence

### QTG-00 — recover before changing

Inspect current ABACUS main, same-day PRs, active branch, latest accepted KEB receipt, current child target and first DOW red. Reuse existing active work where it owns the requested object.

### QTG-01 — validate producer tuple

Before ACCEPT, match producer repo, PR, exact producer head SHA and receipt digest. Missing identity is DEFER; mismatch is REJECT or DEFER depending on whether contradictory evidence is proven.

### QTG-02 — independently challenge or project

Use the smallest existing ABACUS runtime/census/metrics path capable of testing the claim. Do not reimplement KEB semantic ownership or child engineering logic.

### QTG-03 — recurse on first red

Classify the first observed failure as producer identity mismatch, receipt digest missing, execution not observed, runtime dependency, projection contract, source missing, or private-evidence boundary. Repair only that invariant and rerun the same gate.

### QTG-04 — emit DOW disposition

Output exactly one `ACCEPT`, `REJECT` or `DEFER` receipt with the immutable producer tuple, DOW head identity, reason and child re-entry target.

### QTG-05 — child dispatch

Return only the evidence tuple needed by `GBOGEB/cryoplant-project`. DOW cannot turn its own ACCEPT into QPS formal credit.

## 4. Transfer contract

KEB -> DOW:

```yaml
keb_receipt:
  producer_repo: GBOGEB/CODEX
  producer_pr: <number>
  producer_head_sha: <sha>
  result: PASS|FAIL|DEFER
  receipt_sha256: <digest>
  executed_steps: <integer|null>
```

DOW -> child:

```yaml
dow_receipt:
  consumer_repo: GBOGEB/ABACUS
  consumer_pr: <number>
  consumer_head_sha: <sha>
  producer_repo: GBOGEB/CODEX
  producer_pr: <number>
  producer_head_sha: <sha>
  producer_receipt_sha256: <digest>
  challenge_or_execution: <name>
  disposition: ACCEPT|REJECT|DEFER
  reason: <bounded reason>
  child_reentry_target: GBOGEB/cryoplant-project
```

## 5. W107 precedent to preserve

The current positive exemplar is CODEX #600 -> ABACUS #1107: exact CODEX producer head `7f062faf8c76a6e89780bb0fbb1ee1fe96f5af4b`, workflow-generated receipt, real LLDB steps >0, DOW ACCEPT, no child authority transfer. The QTG bridge generalizes that evidence discipline to QPS/TRIAGE session transfer.

## 6. FIFO plus adjacency rule

DOW handles the oldest actionable consumer/challenge blocker first. While already touching the same path, low-cost repairs such as stale federation metadata, missing dependency declaration, or a small regression assertion are allowed. A new dashboard, census family or orchestration abstraction is deferred unless it is needed for the blocking proof.

## 7. MIP mapping inside ABACUS

**Modernize** stale DOW consumer contracts, missing runtime dependencies, duplicate projections and non-executable proof paths.

**Innovate** bounded challenge paths or metrics only where they expose a previously unobservable predicate.

**Perpetuate** only after repeated exact-SHA receipt consumption/challenge succeeds and the history/metrics record is append-only and reproducible.

## 8. Definition of done

For one QPS/TRIAGE item, DOW is done only when producer identity is exact, the requested challenge actually executes where applicable, the output is one evidence-bearing ACCEPT/REJECT/DEFER receipt, private child evidence is not copied, and the receipt can be consumed by cryoplant child authority. No ABACUS-only event changes formal QPS engineering or negotiation credit.

# BD / LDAB / CI / LLDB joined root-cause census

Status: bounded implementation candidate. Tracking: ABACUS #1929.
Source of authority: ABACUS #1860 and #1915; no merger authority.
This is an observational join, not a release or scanner-security gate.

## Evidence inventory (14 October 2026)

- ABACUS exact head:
  18a28e082b64774fb80c5545491e463a8ad77d1d.
- Bandit census run: 38531518523; artifact: 11878347453.
  Its native log recorded 6,393 full and three configured findings.
  Full and configured are different scopes and never subtracted.
- Focused regression: 101 passed; 97/98 lines; 49/50 branches.
  This is not full-repository or changed-line coverage.
- DAB Flake8 run: 38531518566; 2,946 findings.
- MIP B0 run: 38531518608; eight successful proposal jobs.
  No repaired security finding is credited from proposal completion.
- CODEX exact head:
  6e5b54d683a2bc049f4e01048e18c135e84ef61b.
- CODEX real debug run: 38523894832; ten remote LLDB probe steps.
  Container port 4711 mapped to 127.0.0.1:32768 during the run;
  the container was removed in cleanup. This is not a live port now.
- CODEX child-local cryoplant debugger recovery: withheld.
- ABACUS main protected branch: false in the checked snapshot.

The current joiner does not scrape GitHub or fabricate raw reports.
The operator supplies the source artifacts and explicit provenance.

## Input contract

The command reads one JSON object with schema bd.ldab.input.v1.
Required scope keys:

- repository, head_sha, scan_configuration
- run_id, job_id, evidence_url (GitHub source)
- bandit_disjoint (existing bandit.disjoint.census.v1 object)

Optional arrays: ci_failures, debug_receipts.
Optional object: previous (same repository and scanner configuration).

Each CI observation requires repository, source_sha, run_id,
job_id, evidence_url, signature, rule_or_error_code and optional
source_path. Linking to a Bandit root requires the explicit
related_bandit_fingerprint field and an identical repository/head SHA.

Each debugger receipt requires repository, source_sha, run_id, job_id,
evidence_url and nonnegative real_probe_steps. Optional runner_id,
session_id, port_lease_id, container_id, image_digest and host_binding
are retained. A reported session requires both session_id and runner_id
plus a positive real_probe_steps count. These fields remain unverified.
The joiner checks field shape only; external authenticity is not proven.

Cross-repository CODEX runtime receipts remain unlinked observations
until a separate, reviewed producer/consumer authority binding is
implemented. Never turn a matching name into an inferred join.

## Determinism and evidence policy

- No timestamps, random IDs, network calls or source edits in joiner.
- Same input bytes produce identical normalized output bytes.
- Disjoint Bandit rows must reconcile totals and file ownership.
- Invalid paths, missing SHA and duplicate fingerprints fail closed.
- Historical deltas require different SHA and the same declared scan
  configuration. The manifest string alone is not proof that actual
  scanner flags, versions and exclusions were identical.
- Null means unavailable: do not convert missing worker, changed-line
  coverage or debug evidence into zero.
- Terminal hold is always maintained by the diagnostic joiner.
- Any new first red or successor SHA requires a new native producer.
- Exact config digests, source-line movement reconciliation,
  independent security review and effective main protection are
  separate admission requirements.

## CLI and repeatability

Run on a checkout with the source report saved locally:

    python scripts/bd_ldab_join_census.py --input input.json --out join1.json
    python scripts/bd_ldab_join_census.py --input input.json --out join2.json
    cmp join1.json join2.json
    python -m pytest -q tests/test_bd_ldab_join_census.py

Never place security-sensitive raw diagnostics in a public commit.
Publish only appropriately sanitized exact-SHA summaries.

## Mermaid: evidence to repair and admission

Mermaid source: [BD / LDAB joined workflow](BD_LDAB_JOIN_WORKFLOW_20261014.mmd).

The corresponding GitHub issue #1929 also includes a rendered flowchart.

## Ordered traceable work

- J01: validate exact-head inputs and authenticated run/job identity.
- J02: reconcile exclusive B2-B5 owner and Bandit fingerprints.
- J03: classify Flake8/CI signatures and first-red causality.
- J04: attach LDAB/LLDB only through real session evidence.
- J05: compare comparable scanner configurations and deltas.
- J06: measure coverage, runner throughput and retry pressure.
- J07: emit deterministic joins and repeatability tests.
- J08: preserve independent review and protected-branch admission.
- J09: feed two comparable DMAIC cycles into PCA/BT prioritization.

The initial script implements only the offline J01/J02/J03/J04/J05/J07
contract. Native evidence extraction, real-time runner telemetry,
the W84 effectiveness experiment and security disposition remain open.

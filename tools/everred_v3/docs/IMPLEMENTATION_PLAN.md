# EVERRED V3 implementation and evidence register

## Scope and authority

The control plane provides source-bound measurement, coordination,
preview verification, KPI history and recurrence sentinels. It shall
not authorize merges, security waivers or repository-policy changes.

## Work packages

| ID | Lane | Delivered scope | Remaining native gate |
| --- | --- | --- | --- |
| V3-A1 | A | Actions run/job reader | Artifact producer readback |
| V3-A2 | B | Candidate-only native joins | Counterfactual root proof |
| V3-A3 | C | Atomic Git ref leases | Authenticated worker dispatch |
| V3-A4 | D | Immutable Git replay | Native consumer CI |
| V3-A5 | E | Bandit fingerprints | Independent security review |
| V3-A6 | F | Typed RHEL/Docker/LDAB | Real runtime session census |
| V3-A7 | G | Admission evaluator | Effective branch rules |
| V3-A8 | H | Read-only federation path | REX acceptance |
| V3-A9 | M | KPI history and alerts | Two comparable cycles |

## Evidence quality and acceptance

**Input identity:** repository, full source SHA, run/attempt, job, test
or scanner profile, producer version, artifact digest and time source.

**Native source:** GitHub Actions metadata is read-only and authenticated
only when fetched through an authorized API reader. Offline imports
remain self-reported, not independently authenticated.

**Scanning:** full and configured Bandit findings are different scopes.
Raw finding counts are not fingerprint-matched resolved debt. Safety
failure classification is separate from Bandit findings.

**Coverage:** report the scope, unit, numerator, denominator, tool,
configuration and test selection. No eligible lines means N/A.

**Runtime:** RHEL/UBI, Docker, debugger sessions and ports require
exact-source, authenticated job/runner and attached execution data.
A historical mapped port does not establish a presently active port.

**Lease:** the dedicated ref uses server-side Git compare-and-swap.
Expired claims remain owned pending an auditable release or recovery.
An approved source mutation requires independent execution authority.

**Replay:** an isolated preview captures the main-base, consumer and
repair SHAs plus the resulting tree. It is not a native consumer-head
check and has no admission authority.

**KPI:** history pulses preserve numerator and denominator scope and
hash-chain provenance. Alert generation does not establish delivery.

**Governance:** server-read effective rules, eligible independent
approval, resolved review conversations and every applicable mandatory
check must be verified. Missing data stays UNKNOWN and blocks admission.

## DMAIC delivery loop

- **Define:** intended behavior, authoritative requirement and owner.
- **Measure:** native exact-source evidence and scope-bound counters.
- **Analyze:** first-red dependency DAG and counterfactual RCA.
- **Improve:** bounded canonical repair, tests and replay consumers.
- **Control:** immutable histories, recurrence and independent policy.

## Definition of verification

A local repair requires original failure reproduction, a preserved
engineering-intent contract, focused and negative tests, source-bound
receipts and unambiguous mutation authority. Producer PASS is not merge
permission.

## Definition of done

Global closure requires protected admission, independent review,
authoritative security disposition, exact-main verification, all
relevant consumer replay receipts and recurrence observation.

## Previously observed evidence

PR #1914's case-study SHA is
`e9f34b22967064c779891a4d2ac40541f370e812`. Its reported
coverage and Bandit counts remain historical. The later V3 base at
`b45cf45eaad8303c6c4287616492895be4638f56` is a separate
revision. No cross-SHA delta can be inferred from raw counts.

The previously observed V3 draft PR #1933 includes a documentation
validation failure. The relevant source was corrected in this wave
without disabling markdownlint. A new exact-head native run is still
required before crediting that correction as verified.

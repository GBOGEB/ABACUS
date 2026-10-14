# LDAB census and runtime evidence hardening

Issue: ABACUS #1929. Related disjoint join: draft PR #1930.
Scope: existing MIP N2 self-index producer and downstream consumer.
Authority: no source repair admission, security waiver or merge.

## Failure mode and correction

Before this change, root and nested `repo_self_assess_debug_ldab`
returned GREEN when a debug-related filename existed. That status
established neither an executed test nor an authenticated LLDB session.

The hardened schema `mip.ldab.telemetry.v1` in the sanitized N2
summary separates three layers:

1. **SOURCE_DISCOVERY_ONLY**: full root/nested candidate file count,
   bounded sample paths, sample count and truncation status.
2. **FEDERATION_CONTRACT_ONLY**: executed nested diagnostic check count,
   passed/failed denominator, exact parent SHA and source contract digest.
3. **UNKNOWN_NO_RUNTIME_RECEIPT**: native ABACUS LLDB/DAP sessions,
   authenticated port leases, active workers, debugger steps and
   accepted remediations are null, never fabricated zeroes or green.

The root index includes the nested tree. Therefore the two file
counts cannot be added into a deduplicated repository-wide total.
The `combined_candidates` field is null by design.

The original filename detector uses permissive substring matching.
For example, `log` occurs in `catalog` and `topology`;
`dap` occurs in `adaptive`. A 104-file lexical count is not a
104-tool inventory. The producer now also retains every candidate path
and classifies it with explicit, versioned path-component token rules.

The independently enumerated baseline from exact SHA
`a3ccc0bc5ceebe3806f393d507ef3de2e4271408` is:
29 explicit debug/diagnostic names, 29 log/trace-related names,
46 incidental lexical matches (total 104). These are observations,
not repairs, live workers, or executable tool availability.
The new `ldab.lexical.v1` contract shall reproduce these counts
on a source-equivalent inventory or explain changed source membership.

## Evidence fields and invariants

| Key | Source | Meaning |
|---|---|---|
| `repository`, `source_sha` | Git exact checkout | Immutable observation source |
| `source_census.root.candidate_file_count` | MIP root emitter | Debug-associated path count |
| `source_census.root.sample_paths` | MIP root emitter | First 20 sorted relative paths |
| `source_census.nested.candidate_file_count` | Nested MIP emitter | Nested local path count |
| `source_census.nested.sample_paths` | Nested emitter | First 12 sorted relative paths |
| `source_census.*.sample_truncated` | Computed | Full count exceeds sample |
| `source_census.*.full_source_inventory` | Exact tree | Every relative candidate path + source class |
| `source_census.*.source_class_counts` | Versioned tokens | Explicit debug / logs / incidental |
| `diagnostic_execution.contract_checks_total` | Executed diagnostic | Federation contract checks, not debugger steps |
| `diagnostic_execution.source_contract_sha256` | Diagnostic receipt | Test-contract content identity |
| `runtime.abacus_native_debug_sessions` | Not produced here | Always null, not zero |
| `runtime.authenticated_port_leases` | Not produced here | Always null, not zero |
| `runtime.ldab_verified_repairs` | Not produced here | Always null, not zero |
| `merge_admission` | Read-only report | HOLD independently of tests |

The source-level `green` from the legacy MIP assessment is retained
for backwards-compatible discovery status only. The telemetry exposes
`evidence_level=SOURCE_DISCOVERY_ONLY` and
`live_runtime_inferred=false` to prevent reinterpretation.

## Native verification

The existing MIP N2 workflow runs the focused stdlib unittest suite
and its existing two-pass SHA-normalized source index generation.
Its consumer validates the new source counts and executed nested
contract counts, and rejects any missing or claimed native runtime
proof within this source-only producer.

Commands:

    python -m unittest discover -s tests -p test_mip_ldab_telemetry.py -v
    python scripts/mip_verify_self_index.py --summary /tmp/mip-summary.json

Only the first command is portable outside a repository checkout.
The second requires a checked-out exact Git commit and all federation
contracts; the CI workflow supplies that controlled environment.

## Testflight and hardening priorities

| ID | Goal | DoV |
|---|---|---|
| L01 | Validate repo, exact SHA and file census scope | Invalid SHA rejected |
| L02 | Enumerate root path count and sample coverage | Nonnegative full count |
| L03 | Enumerate nested path count separately | No duplicate summation |
| L04 | Reject path traversal, duplicates and malformed denominators | Negative tests fail closed |
| L05 | Bind nested federation execution to SHA and contract digest | Count positive and all checks PASS |
| L06 | Reject green despite missing/failed native diagnostic | Negative tests fail closed |
| L07 | Produce two normalized repeatable receipts | Identical digests |
| L08 | Upload sanitized telemetry and verify consumer | Both workflow jobs pass on same SHA |
| L08b | Enumerate and classify every source candidate | Full paths/counts reconcile; no substring false authority |
| L09 | Add separate real debugger/protocol/port producer | Authenticated run/job/session/steps/port receipt |
| L10 | Reconcile persistent root IDs to repair and consumer replay | Accepted source-bound repair lineage |

L01-L08 are implementation candidates until native exact-head CI passes.
L09-L10 are deliberately not credited by this patch.

[Mermaid source](LDAB_TELEMETRY_WORKFLOW_20261014.mmd).

## Operational telemetry unavailable in MIP N2

The GitHub Actions producer does not inspect a running Docker daemon,
collect LLDB commands, lease localhost ports, launch repair workers or
approve repairs. Those facts require independently authenticated
runtime and engineering producers. A valid federation smoke check
must not increase their numerators.

Historical CODEX runtime executions may be correlated only as separate
observations, not as evidence of current ABACUS debugger uptime.

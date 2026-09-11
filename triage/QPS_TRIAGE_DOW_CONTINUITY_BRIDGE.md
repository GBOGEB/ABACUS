# QPS / TRIAGE DOW Continuity Bridge

Purpose: make DOW the document-oriented governance consumer for the QPS/TRIAGE chat-to-GitHub continuity contract.

## Intake

For every execution pulse, DOW shall consume:
- session manifest
- artifact register
- active PR/branch/SHA census
- typed findings and evidence class
- DoD/DoV state
- next-action pointer

## Governance rules

1. Re-enter from current GitHub state before interpreting chat history.
2. Preserve source class: immutable, source-supported, derived, postulated.
3. Do not promote DEFER to PASS.
4. Preserve repo/PR/SHA lineage for triage claims.
5. Preserve OFFER/RTM/EVAL and agenda links for QPS content.
6. Prefer extending an existing canonical object or PR over creating a parallel framework.
7. Apply FIFO to blocking work, but execute low-risk blocker removals immediately.

## DOW output contract

Each pulse should emit a governed record with:
- pulse_id
- source_chat_ref
- affected_repositories
- affected_prs
- exact_head_shas
- changed_artifacts
- evidence_class
- disposition
- dod_state
- dov_state
- next_action

## Expedition Project Manager secondment

DOW may second a **Project Manager (PM)** into a temporary QPS TRIAGE / Elastic Expedition mission.
The PM is the mission delivery authority, not the runtime scheduler.

PM owns:
- mission charter and scope boundary
- WBS / work graph
- dependencies
- Wave/Pulse sequencing
- resource and crew budget
- risks / issues / actions
- DoD tracking
- delivery closure
- return / stay / reinforcement recommendation
- synchronization with the DOW work graph

Authority separation:

```text
PM
  defines and controls the work to be delivered
  |
  v
The_Orchestrator
  chooses the next executable worker/tool from current receipts
  |
  v
Workers -> observed receipts
  |
  v
PM updates delivery state
```

Observed execution remains ground truth. PM must not convert queued, intended, merged, or statically inspected work into runtime PASS.

### PM outbound secondment tuple

When DOW seconds a PM, the mission handoff should carry:

```text
mission_id
objective
priority
scope_boundary
current_wave
current_pulse
work_graph_ref
ready_work
blocked_work
deferred_work
resource_budget
current_crew
BG
CG
dod_state
source_repo_pr_sha_bindings
```

### PM return-home tuple

When the mission contracts or closes, PM returns to DOW with:

```text
mission_id
completed_work
blocked_work
deferred_work
residual_actions
dependency_state
resource_use
crew_return_state
final_or_current_dod_state
dov_state
exact_receipt_bindings
next_action_or_closure_reason
```

Worker-level return is not mission closure. DOW may only close mission delivery when the governing PM acceptance gate is satisfied or the mission has a controlled PARK / ARCHIVE / PRUNE disposition.

## Management-gate participation

For expedition victories:
- DoV-1 requires `PM delivery = ACCEPT` in addition to technical/runtime/QA/Governor gates.
- DoV-2 additionally requires DOW work closure bound to the independent consumer receipt.
- DoV-3 requires the work to have entered a recurrent Control state rather than depending on expedition memory.

## Definition of done

DOW-side continuity is complete when an inbound chat/session can be reduced to a source-bound governed record, linked to the affected QPS/TRIAGE artifacts, and handed to KEB without losing lineage or introducing unsupported authority.

For seconded expedition work, continuity is additionally complete only when the PM return-home tuple has been reconciled into the DOW work graph or a controlled open action remains.
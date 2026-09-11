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

## Definition of done

DOW-side continuity is complete when an inbound chat/session can be reduced to a source-bound governed record, linked to the affected QPS/TRIAGE artifacts, and handed to KEB without losing lineage or introducing unsupported authority.

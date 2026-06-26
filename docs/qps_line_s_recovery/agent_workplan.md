# Parallel Agent Workplan

## Program model

The QPS Line S recovery package is executed as a wave program.

### Wave W001 - Reduced recovery model scaffold

Goal: produce a traceable first-order model and Applicant-response package.

Status: active draft in PR #582.

### Wave W002 - Scenario and RTM completion

Goal: complete scenario matrix, RTM traceability, and confirmation register.

Lead: Agent A.

### Wave W003 - Model validation and output generation

Goal: add structured scenario input data, validation runner, and CSV or JSON outputs.

Lead: Agent B.

### Wave W004 - Mode and valve-state extraction

Goal: extract Appendix 8.4 mode drawings into valve-state tables and recovery path states.

Lead: Agent A with review by owner.

### Wave W005 - Property and transient upgrade

Goal: add optional CoolProp support, volume and temperature sensitivity, and transient inflow profiles.

Lead: Agent B.

### Wave W006 - Applicant response release package

Goal: consolidate final technical note, model outputs, assumptions, and open confirmations.

Lead: assistant and owner.

## Active helper issues

| Helper | Repo | Issue | Focus |
|---|---|---:|---|
| Agent A | GBOGEB/ABACUS | 583 | Documentation, traceability, scenario matrix |
| Agent B | GBOGEB/ABACUS | 584 | Python model, validation runner, outputs |
| CODEX helper | GBOGEB/CODEX | 237 | Reusable index, glossary, manifest workflow |

## Merge discipline

1. Keep W001 PR open as draft until Agent A and Agent B outputs are either merged into branch `w001` or explicitly deferred.
2. Every new file must appear in `index.json`.
3. Every new term must be added to `glossary.md` or later `glossary.yaml`.
4. Every model extension must update `progress_21_point.md`.

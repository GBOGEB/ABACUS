# CODE_MAROON

CODE_MAROON is the repository-level review and security debt control plane.

It does not replace CODE PURPLE, the GitHub Security tab, CodeQL, Semgrep,
Bandit, OSV, Codex review, Copilot review, branch protection or independent
approval. It reconciles their findings into one auditable snapshot so merge
blockers are not hidden across PR conversations.

## Accounting model

A manifestation is one actionable inline review/security finding.

A root is one causal repair unit. Multiple comments may map to one root when
they describe the same defect and share one repair contract. Different lines
are not collapsed merely because they use the same tool/rule.

Review summary comments are metadata, not findings. Resolved findings remain
in the historical total.

Statuses:
- CLOSED_IMPLEMENTED: source repair present and thread closed.
- OPEN_ACTIVE: source/root work still required.
- DEFERRED_OWNER: routed to a canonical owner rather than duplicated here.

Every pulse reports total manifestations, implemented, closed/resolved,
deferred, outstanding, active failing, and total/closed/deferred/open roots.

## Security sources

Existing native producers are reused:
- Semgrep SARIF: .github/workflows/semgrep.yml
- Bandit SARIF: .github/workflows/bandit.yml
- OSV Scanner: .github/workflows/osv-scanner.yml
- CodeQL: GitHub code scanning
- Codex code/security review: PR review threads
- Copilot review: PR review threads

SARIF fingerprints are useful dedupe candidates, but do not automatically
become causal roots. CODE_MAROON root_id is the governed root identity.

## OOXML

OOXML scanning is enabled as a bounded lane for tracked DOCX/XLSX/PPTX and
macro-enabled OOXML packages. It inspects ZIP structure, external relationships,
embedded objects/macros, path traversal, malformed packages and decompression
limits without extracting package members. HIGH structural hazards fail the
MAROON workflow; MEDIUM macro/external-link findings remain explicit review debt.

## Control boundary

CODE_MAROON never authorizes merge, dismisses a genuine security finding,
changes scanner severity, or converts UNKNOWN to PASS. Closing a thread means
the exact source request is implemented or explicitly dispositioned; native CI
and security gates remain independent.

## Test-discovery preflight / fail-closed Testflight

Canonical PR/push SHA is checked against actual checkout HEAD before evidence is run.
Stdlib AST preflight verifies the presence of pytest functions in the required
reconcile, OOXML and negative-control suites. Preflight is declarations-only and
does not count as executed tests. Pinned pytest then emits JUnit. A separate
stdlib verifier rejects zero, malformed, skipped, failing, duplicated or
missing-cohort JUnit and writes source-labelled JSON and SHA-256 receipts.
GitHub run/job identity, accepted REX and independent P0 admission remain
independent requirements.

Quick local commands on a trusted exact checkout:

    python tools/code_maroon/testflight_guard.py preflight
    python -m pytest -q tests/test_code_maroon_reconcile.py tests/test_code_maroon_ooxml.py tests/test_code_maroon_testflight.py --junitxml=maroon.xml
    python tools/code_maroon/testflight_guard.py verify --junit maroon.xml --source-sha "$(git rev-parse HEAD)" --out maroon.json

The existing EVERRED SUT GUI and W169 QPLANT Kubernetes workflow remain the
canonical local quick-run and container-runtime surfaces. Do not duplicate
dispatch authority in CODE_MAROON.

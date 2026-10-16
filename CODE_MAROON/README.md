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

OOXML scanning is a candidate lane when DOCX/XLSX/PPTX or other OOXML packages
enter the security scope. A bounded check should inspect ZIP structure,
external relationships, embedded objects/macros, path traversal, malformed
XML, and decompression limits. It should not be enabled merely to inflate
scanner count when no OOXML artifacts are in scope.

## Control boundary

CODE_MAROON never authorizes merge, dismisses a genuine security finding,
changes scanner severity, or converts UNKNOWN to PASS. Closing a thread means
the exact source request is implemented or explicitly dispositioned; native CI
and security gates remain independent.

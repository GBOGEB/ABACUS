# Governance Framework — `<repo-name>`

**Phase:** 5 — DMAIC Control
**Date:** YYYY-MM-DD

The rules that keep the repository from regressing.

---

### 1. Branch protection (main)

Enforced via GitHub Branch protection rules:

- Require pull request reviews before merging (≥ 1 approver).
- Dismiss stale pull request approvals when new commits are pushed.
- Require status checks to pass (list: `ci`, `lint`, `test`, `docs-build`).
- Require branches to be up to date before merging.
- Restrict who can push to matching branches: (admins only or empty).
- Include administrators in restrictions.
- Disallow force pushes.
- Disallow deletions.

### 2. CODEOWNERS

`.github/CODEOWNERS` maps every top-level directory to one or more owners. PR review is required from the matching owner.

### 3. Issue / PR templates

| Template                              | Path                                              |
| ------------------------------------- | ------------------------------------------------- |
| Bug report                            | `.github/ISSUE_TEMPLATE/bug_report.md`            |
| Feature request                       | `.github/ISSUE_TEMPLATE/feature_request.md`       |
| Documentation improvement             | `.github/ISSUE_TEMPLATE/documentation_improvement.md` |
| Question                              | `.github/ISSUE_TEMPLATE/question.md`              |
| Pull request                          | `.github/PULL_REQUEST_TEMPLATE.md`                |
| Release notes                         | `.github/RELEASE_TEMPLATE.md`                     |

### 4. Release policy

- Versioning: SemVer (`MAJOR.MINOR.PATCH`).
- Every release is tagged (`vX.Y.Z`) and triggers `release.yml`.
- `CHANGELOG.md` updated **before** the tag.
- Breaking changes require a major version bump.
- Deprecated APIs are warned for one minor cycle before removal.

### 5. Security

- `SECURITY.md` documents the disclosure process.
- Dependabot / Renovate enabled for dependency updates.
- CodeQL or equivalent SAST scanning enabled.
- Secrets scanning enabled in repository settings.

### 6. Roles

| Role          | Permissions                       | Responsibilities                          |
| ------------- | --------------------------------- | ----------------------------------------- |
| Maintainer    | Admin                             | Final approval, releases, branch protect. |
| Contributor   | Triage / Write on PR branches    | Code, tests, docs.                        |
| Reviewer      | Write                             | Code review, sign-off.                    |
| Reporter      | Read                              | File issues, comment on PRs.              |

### 7. Decision log

Architectural decisions are recorded in `docs/decisions/ADR-<n>-<title>.md` (Architecture Decision Records).

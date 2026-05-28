# Target Structure — `<repo-name>`

**Phase:** 4 — DMAIC Improve
**Date:** YYYY-MM-DD

The ideal layout the repository should have *at the end of Phase 4*.

---

### Proposed tree

```
<repo>/
├── .github/
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── CONTRIBUTING.md
│   └── CODEOWNERS
├── docs/
│   ├── index.html
│   ├── handover_book.html
│   ├── api/
│   ├── assets/
│   └── <topic-pages>/
├── docs_versioned/
│   ├── v<n.m>/
│   └── DEPRECATION_NOTICES.md
├── src/  (or domain-specific name)
├── tests/
├── scripts/
├── README.md
├── CHANGELOG.md
├── LICENSE
└── SECURITY.md
```

---

### Move plan (file-by-file)

| From                                  | To                                       | Tag from classifier |
| ------------------------------------- | ---------------------------------------- | ------------------- |
|                                       |                                          |                     |

---

### Naming standards adopted

- Python modules: `snake_case.py`
- Markdown reports: `SCREAMING_SNAKE.md`
- Workflows: `kebab-case.yml`
- Branches: `feature/*`, `fix/*`, `dmaic/phase-N-*`

---

### Out of scope (explicit)

- Files / directories *not* moving and why.

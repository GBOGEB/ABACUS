# Contributing to `<repo-name>`

Welcome! This document is the contract between contributors and the repository.

---

### How to contribute

1. **Fork** the repository and clone your fork.
2. Create a **branch**: `feature/<short-description>` or `fix/<short-description>`.
3. Make your changes in small, focused commits.
4. **Test** locally: `pytest` (Python) / `npm test` (JS) / language equivalent.
5. **Lint**: `ruff check .` / `eslint .` / language equivalent.
6. Push your branch and open a **Pull Request** against `main`.
7. Fill out the PR template completely.
8. Request review from a CODEOWNER.

### Commit message style

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`.

### Code style

- Python: PEP 8, type hints encouraged, docstrings required on public APIs.
- JS / TS: project Prettier + ESLint config.
- Markdown: 1 sentence per line for diffability; reference-style links allowed.

### Testing

- All new public APIs must have unit tests.
- Bug fixes must include a regression test.
- Coverage target: ≥ 80% on modified files.

### Documentation

- Code changes that affect behavior must update:
  - The relevant section README.
  - `CHANGELOG.md` under "Unreleased".
  - Any user-facing docs in `docs/`.

### Review process

- At least **1 approving review** from a CODEOWNER.
- All required status checks must pass.
- Squash-merge by default; rebase-merge by reviewer discretion.
- No force-push to `main` ever. Force-push to feature branches is allowed.

### Reporting issues

Use the appropriate template in `.github/ISSUE_TEMPLATE/`:

- 🐛 Bug report
- ✨ Feature request
- 📝 Documentation improvement
- ❓ Question

### Security

Do **not** open public issues for security problems. Email the maintainers as described in `SECURITY.md`.

### License

By contributing you agree that your contributions are licensed under the project's `LICENSE`.

---

Thank you for contributing! 🎉

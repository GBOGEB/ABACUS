---
title: Performing ABACUS integration and smoke tests
shortTitle: Performing tasks
intro: 'How to set up, smoke test, and document ABACUS alongside CODEX and morris.js. Prerequisites and step-by-step procedure.'
type: how_to
---

## Prerequisites

- Write access to GBOGEB/ABACUS or an ability to open pull requests.
- Basic familiarity with git, JavaScript, and Markdown for docs curation.
- Node.js and a small static web server to smoke-test HTML examples locally (optional).

## Procedure

1. Clone the ABACUS repository:
   - `git clone https://github.com/GBOGEB/ABACUS.git`
   - `cd ABACUS`
2. Create a branch for documentation changes:
   - `git checkout -b docs/add-docs-hub`
3. Add or update docs under the `docs/` folder using the templates in this site.
4. Smoke-test example files (if present) locally. For example, open `examples/area-as-line.html` from morris.js in a browser or serve it locally to verify it renders.
5. Commit and push the branch and open a pull request to the default branch.

## Publishing

- Push commits and open a PR. Once merged, enable GitHub Pages for the repository under Settings → Pages, pointing to the `docs/` folder on the default branch.

## Further reading
- [About ABACUS](about-subject.md)
- [Reference and definitions](reference.md)

# ABACUS Docs Patch

This single file contains all documentation artifacts added to the docs/ directory. It can be used as a single patch or unpacked to recreate the docs site.

---

## docs/index.md

```markdown
---
title: Project documentation index
shortTitle: Docs index
---

# ABACUS Documentation Hub

Abstract:
This site collects the ABACUS project documentation and provides a cross-repo bridge to related managed repositories such as CODEX and morris.js. It contains conceptual, procedural, and reference articles and is GitHub Pages-ready under the docs/ folder.

## Main Repositories and Bridges

Repositories covered and smoke-tested for integration:
- <a href="https://github.com/GBOGEB/ABACUS">GBOGEB/ABACUS</a> — this repository (doc home)
- <a href="https://github.com/GBOGEB/CODEX">GBOGEB/CODEX</a> — coding standards, conventions
- <a href="https://github.com/GBOGEB/morris.js">GBOGEB/morris.js</a> — charting examples referenced here

Further reading:
- <a>About ABACUS and its role</a>
- <a>Performing the main tasks: workflows and smoke tests</a>
- <a>Reference — configuration and terms</a>

## Multi-repo site pattern

This documentation site presents a grouped structure, with content from forked or cloned main repositories collapsed for navigation, integration, and handoff. To assimilate new forks, follow the instructions in the procedural article.

## Manifest, README, and packaging

- Site manifest: <a>manifest.yml</a>
- Packaging: use the Makefile at repo root to produce a zip that contains docs/ and the patch file.

---
```

## docs/content/about-subject.md

```markdown
---
title: About ABACUS and integrated tooling
shortTitle: ABACUS overview
intro: 'Overview of ABACUS and how it connects with CODEX and morris.js for visualization and computation.'
type: overview
---

## ABACUS in context

ABACUS provides computational tooling and processing primitives used across the GBOGEB organization. This site documents ABACUS concepts, procedures for smoke-testing integrations, and reference material for common artifacts.

## Integrating with CODEX and morris.js

This docs hub links shared articles and code references for assimilated repositories — including CODEX and morris.js — providing harmonized access to coding standards and charting examples.

## Further reading

- <a>How to run smoke-tests and publish docs</a>
- <a>Reference materials and configuration</a>
```

## docs/content/how-to-task.md

```markdown
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
- <a>About ABACUS</a>
- <a>Reference and definitions</a>
```

## docs/content/reference.md

```markdown
---
title: ABACUS and integrated reference
shortTitle: ABACUS reference
intro: 'Reference guide for ABACUS terms and cross-repo examples.'
type: reference
---

## Example: area-as-line (from morris.js examples)

Reference usage of an area chart behaving like a line (see examples in morris.js):

```js
Morris.Area({
  element: 'graph',
  behaveLikeLine: true,
  data: [
    {x: '2011 Q1', y: 3, z: 3},
    {x: '2011 Q2', y: 2, z: 1},
    {x: '2011 Q3', y: 2, z: 4},
    {x: '2011 Q4', y: 3, z: 3}
  ],
  xkey: 'x',
  ykeys: ['y', 'z'],
  labels: ['Y', 'Z']
});
```

## Cross-repo links
- <a href="https://github.com/GBOGEB/ABACUS">GBOGEB/ABACUS</a>
- <a href="https://github.com/GBOGEB/CODEX">GBOGEB/CODEX</a>
- <a href="https://github.com/GBOGEB/morris.js">GBOGEB/morris.js</a>
```

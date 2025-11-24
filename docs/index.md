---
title: Project documentation index
shortTitle: Docs index
---

# ABACUS Documentation Hub

Abstract:
This site collects the ABACUS project documentation and provides a cross-repo bridge to related managed repositories such as CODEX and morris.js. It contains conceptual, procedural, and reference articles and is GitHub Pages-ready under the docs/ folder.

## Main Repositories and Bridges

Repositories covered and smoke-tested for integration:
- [GBOGEB/ABACUS](https://github.com/GBOGEB/ABACUS) — this repository (doc home)
- [GBOGEB/CODEX](https://github.com/GBOGEB/CODEX) — coding standards, conventions
- [GBOGEB/morris.js](https://github.com/GBOGEB/morris.js) — charting examples referenced here

Further reading:
- [About ABACUS and its role](content/about-subject.md)
- [Performing the main tasks: workflows and smoke tests](content/how-to-task.md)
- [Reference — configuration and terms](content/reference.md)

## Multi-repo site pattern

This documentation site presents a grouped structure, with content from forked or cloned main repositories collapsed for navigation, integration, and handoff. To assimilate new forks, follow the instructions in the procedural article.

## Manifest, README, and packaging

- Site manifest: [manifest.yml](../manifest.yml)
- Packaging: use the Makefile at repo root to produce a zip that contains docs/ and the patch file.

---

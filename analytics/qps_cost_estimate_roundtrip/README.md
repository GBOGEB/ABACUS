# QPS Cost Estimate Roundtrip

Status: Wave 1 bootstrap
Control ID: GOV-001
Canonical analytics repository: `GBOGEB/ABACUS`

## Purpose

This module defines the controlled roundtrip for the QPS cost-estimate project:

```text
GitHub text source
  -> clean local clone outside OneDrive
  -> isolated build workspace
  -> QA, rendering, lineage and hashes
  -> immutable release export to OneDrive
  -> Office review copy
  -> approved changes assimilated into text SSOT
  -> new branch / pull request / rebuild
```

The roundtrip is intentionally one-directional at release time. Office files are review artifacts, not direct Git inputs.

## Repository boundaries

| Repository | Role | Allowed QPS content | Excluded content |
|---|---|---|---|
| `GBOGEB/ABACUS` | Canonical QPS analytics, cost methodology, SSOT schemas, semantic output contracts | Generic code, text SSOT schemas, synthetic fixtures, analytics tests, methodology documentation | Confidential bidder data, evidence PDFs, generated Office/PDF binaries |
| `GBOGEB/CODEX` | Federation, runtime governance, CI templates, release and hash tooling | Generic scripts and reusable governance templates | QPS commercial values, QPS-specific confidential source text, generated binaries |
| `GBOGEB/DOCX_RTM_Automation` | Word/RTM document-generation adapters | Generic document builders and tests | Canonical QPS analytics or confidential evidence |
| `GBOGEB/cryoplant-project` | Private QPS overlay for project-specific text SSOT and evidence registry | Confidential text configuration, source hashes, mapping tables, release config | Evidence binaries and generated release binaries by default |

`ABACUS` remains the canonical repository for QPS analytics. `CODEX` is limited to reusable governance and federation tooling.

## Storage boundaries

### Local repositories

```text
C:\DEV\REPOS\
  ABACUS\
  CODEX\
  DOCX_RTM_Automation\
  cryoplant-project\
```

### Disposable build workspaces

```text
C:\DEV\WORKSPACES\qps-cost\
  <version>_<commit>_<build-id>\
    input\
    build\
    render\
    qa\
    dist\
```

The build workspace is not a Git working tree and can be deleted and rebuilt.

### OneDrive release area

```text
<OneDriveRoot>\QPS\Cost Estimate\
  00_EVIDENCE\
  10_RELEASES\
  20_WORKING_REVIEW\
  90_ARCHIVE\
```

- `00_EVIDENCE`: controlled source files used by the build.
- `10_RELEASES`: immutable, versioned, hash-bound outputs.
- `20_WORKING_REVIEW`: editable Office copies.
- `90_ARCHIVE`: superseded releases.

## Binary policy

The new QPS roundtrip paths are text-source only. The following are not committed:

```text
.xlsx .xlsm .docx .pptx .pdf .png .jpg .jpeg .zip .tar .tar.gz
```

External evidence remains outside Git and is referenced by an evidence registry containing expected filename, classification, size and SHA-256.

## Hash classes

1. **Source-tree hash**: text SSOT, source, templates and tests.
2. **Evidence hash**: external source files in the controlled evidence vault.
3. **Semantic output hash**: normalized workbook/document/deck model content.
4. **Artifact hash**: exact released binary bytes for integrity after publication.

A raw Office-file hash proves the integrity of a specific release. It does not by itself prove future byte-for-byte reproducibility.

## Wave plan

### W000 - Boundary and audit

- [x] Confirm repository roles.
- [x] Keep QPS analytics canonical in ABACUS.
- [x] Establish public/private content boundary.
- [x] Create dedicated implementation branches.

### W001 - Bootstrap

- [x] Add this architecture and release contract.
- [ ] Add generic local bootstrap and release scripts in CODEX.
- [ ] Add private overlay templates in `cryoplant-project`.
- [ ] Open draft pull requests for review.

### W002 - Reproducible clean-clone build

- [ ] Verify source and evidence hashes before build.
- [ ] Build XLSX, DOCX, PPTX, PDF and HTML outside repositories.
- [ ] Generate QA report, recursive manifest and build metadata.
- [ ] Run clean-clone rebuild and semantic comparison.

### W003 - OneDrive publication

- [ ] Publish to a versioned immutable release folder.
- [ ] Re-hash at destination and compare with local manifest.
- [ ] Create a separate Office review copy.
- [ ] Prevent working-review edits from overwriting releases.

### W004 - Assimilation roundtrip

- [ ] Register Office review changes.
- [ ] Classify each change as data, logic, narrative or formatting.
- [ ] Assimilate approved changes into text SSOT or source.
- [ ] Rebuild and issue a new versioned release.

### W005 - Hardening

- [ ] Add path-scoped CI binary guards.
- [ ] Add release policy tests.
- [ ] Add deterministic OOXML normalization where practical.
- [ ] Add signed tags or release attestations where appropriate.

## Acceptance gates

A release is valid only when:

```text
[PASS] clean clone
[PASS] locked dependencies
[PASS] evidence files found
[PASS] evidence hashes match
[PASS] text SSOT validates
[PASS] workbook formulas validate
[PASS] DOCX, PPTX, PDF and HTML render
[PASS] semantic hashes generated
[PASS] artifact hashes generated
[PASS] OneDrive destination hashes match
[PASS] source commit recorded in BUILD_META.json
```

## Current wave stop point

Wave 1 stops after draft PRs establish the source boundaries, templates and local tooling. No confidential source files or generated binaries are moved into GitHub during this wave.

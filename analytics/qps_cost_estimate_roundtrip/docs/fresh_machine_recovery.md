# QPS Cost Estimate — Fresh Machine Recovery

Control ID: GOV-001

## Goal

Recover the QPS cost-estimate build environment on a new Windows machine without copying an old Git working tree or treating prior Office binaries as source.

## Preconditions

- Git available.
- PowerShell available.
- Python/runtime dependencies available per locked project requirements.
- Microsoft Office / PDF / browser rendering tools available where required by QA.
- Access to the private `cryoplant-project` repository.
- Access to the controlled OneDrive evidence vault.

## 1. Create clean local roots

```text
C:\DEV\REPOS
C:\DEV\WORKSPACES\qps-cost
```

Do not put active Git repositories inside OneDrive.

## 2. Clone the repositories from GitHub

```text
GBOGEB/ABACUS
GBOGEB/CODEX
GBOGEB/cryoplant-project
GBOGEB/DOCX_RTM_Automation
```

Record the checked-out commit SHA for every repository.

## 3. Bind external storage

Set process/user environment variables:

```text
QPS_EVIDENCE_ROOT=<OneDriveRoot>\QPS\Cost Estimate\00_EVIDENCE
QPS_RELEASE_ROOT=<OneDriveRoot>\QPS\Cost Estimate\10_RELEASES
```

Use the merged CODEX `Start-QpsWave2.ps1` entry point to initialize/verify the local structure.

## 4. Verify evidence before building

The private evidence registry is authoritative for required evidence IDs, relative paths, sizes and SHA-256.

The build must stop when:

- a required file is absent;
- file size differs;
- SHA-256 differs;
- registry status is partial/pending;
- an unapproved substitute file is supplied.

## 5. Build outside Git working trees

Use a new release workspace:

```text
C:\DEV\WORKSPACES\qps-cost\<release-id>\
  input\
  build\
  render\
  qa\
  dist\
```

Generated XLSX/DOCX/PPTX/PDF/HTML and image outputs stay here until publication.

## 6. Verify with a second clean clone

Create a separate verification clone/worktree and repeat the build from the same source commits and evidence registry.

Compare semantic manifests. Do not require raw OOXML bytes to match if only excluded volatile packaging metadata differs.

## 7. Publish only after all gates pass

Publish the completed `dist` directory through `Publish-QpsRelease.ps1`.

Required behavior:

- refuse an existing release destination;
- copy into a versioned immutable release folder;
- recalculate destination hashes;
- compare local and destination hashes;
- create a physically separate Office review copy when requested.

## 8. Office edits return through source

Do not replace the immutable release after Office review.

Record requested changes, classify them as DATA / CALCULATION_LOGIC / NARRATIVE / FORMATTING, normalize them into source, open a PR, rebuild, and publish a new release ID.

## Recovery acceptance

Recovery is complete only when a brand-new clone plus verified evidence can rebuild a release that passes:

- source validation;
- evidence verification;
- formula/structure validation;
- visual rendering QA;
- semantic comparison;
- artifact hashing;
- publication hash verification.

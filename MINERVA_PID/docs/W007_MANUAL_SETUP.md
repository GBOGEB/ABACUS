# W007 — Manual CI/CD Setup Guide

This guide explains how a repository **maintainer** activates the MINERVA P&ID
CI pipeline. The workflow is fully written and validated, but staged at
`MINERVA_PID/ci/minerva-pid-test.yml` instead of `.github/workflows/` because
the connected Abacus GitHub App lacks the `workflows` permission scope and
therefore cannot push files into `.github/workflows/`.

> **One-time maintainer action required.** Until the steps below are done, no CI
> runs will trigger.

---

## 1. Why this is staged (the `workflows` permission blocker)

GitHub treats `.github/workflows/*.yml` as privileged. An OAuth/App token
without the `workflows` scope is rejected when it tries to add or modify those
files. The Abacus App connection used for automated pushes does not currently
hold that scope, so the workflow was committed to a neutral path (`ci/`) that
any token may write.

You have two ways to resolve it (pick one):

### Option A — Grant the permission (recommended, keeps automation)
1. Open the [Abacus GitHub App installation settings](https://github.com/apps/abacusai/installations/select_target).
2. Select this repository (or the org), and grant **Read and write** access to
   **Workflows**.
3. Re-run the automation / re-push; the file can then be placed directly under
   `.github/workflows/`.

### Option B — Land it manually (no permission change)
A human with normal push rights moves the file:

```bash
git switch -c ci/activate-minerva-workflow
git mv MINERVA_PID/ci/minerva-pid-test.yml .github/workflows/minerva-pid-test.yml
# golden_gate.py stays in ci/ — the workflow calls it as ci/golden_gate.py
git add .github/workflows/minerva-pid-test.yml
git commit -m "ci: activate MINERVA P&ID test & reproducibility workflow"
git push -u origin ci/activate-minerva-workflow
```

> **Path note:** The workflow runs with `working-directory: MINERVA_PID` and
> invokes `ci/golden_gate.py` (relative to that directory). Keep
> `MINERVA_PID/ci/golden_gate.py` in place — only the `.yml` needs to move into
> `.github/workflows/`.

Open a PR from that branch and merge once the run is green (see §4).

---

## 2. Step-by-step: create `.github/workflows/`

If the repo has no `.github/workflows/` directory yet:

```bash
# from the repository root
mkdir -p .github/workflows
git mv MINERVA_PID/ci/minerva-pid-test.yml .github/workflows/minerva-pid-test.yml
git add .github/workflows/minerva-pid-test.yml
git commit -m "ci: add MINERVA P&ID workflow"
git push
```

GitHub auto-detects the file on push and registers the workflow under the
**Actions** tab. No further UI configuration is needed.

---

## 3. Permission & environment requirements

| Requirement | Detail |
|---|---|
| Workflow scope | Needed only to *write* the file (see §1). Not needed to *run* it. |
| `permissions:` in workflow | `contents: read` only — CI never writes back to the repo. |
| Secrets | **None.** No tokens, registries, or external services are used. |
| Runner | GitHub-hosted `ubuntu-latest`. No self-hosted runner required. |
| Actions enabled | Settings → Actions → General → "Allow all actions" (or allow `actions/*`). |
| Branch protection (optional) | Add the check **"build + test (py3.10/3.11/3.12)"** as a required status check on `main`. |

---

## 4. Expected CI behavior

On every **push to `main`**, **pull request targeting `main`**, or manual
**Run workflow** dispatch, three parallel jobs run (Python 3.10, 3.11, 3.12).
Each job:

1. **Checkout** the repo.
2. **Set up Python** (with pip cache keyed on `requirements.txt`).
3. **Install system deps:** `poppler-utils`, `libcairo2-dev` (cairosvg needs Cairo).
4. **Install Python deps** from `MINERVA_PID/requirements.txt`.
5. **Reproducibility:** `./make.sh --clean` then `./make.sh` — regenerates every
   derived artifact from tracked source in `data/svg/`. Must exit 0 (this is a
   7-stage integration test by itself).
6. **Test suite:** loops over `tests/test_*.py`, running each standalone runner
   with `PYTHONPATH=src python3 <file>`. Any non-zero exit fails the job.
   Current battery is 50 assertions across 6 suites.
7. **Coverage (optional):** installs `pytest`/`coverage` and emits
   `reports/coverage.xml`. This step is `continue-on-error` — informational only.
8. **Golden-file gate:** `ci/golden_gate.py` semantically diffs regenerated
   `reports/*_statistics.json` against the committed golden snapshots. Fails on
   any count drift; ignores the documented ~1-byte XLSX zip jitter.
9. **Upload artifacts:** `publish/*.html`, `reports/*.md`,
   `reports/*_statistics.json`, `data/crossmap/*.json`, `coverage.xml`
   (downloadable from the run page for 14 days).

**Green run = ** all three Python versions reproduced artifacts, passed every
test, and matched the golden statistics.

### Add a status badge (deliverable §6 of the plan)
After the workflow is on `main`, add to the README:

```markdown
![CI](https://github.com/<owner>/<repo>/actions/workflows/minerva-pid-test.yml/badge.svg)
```

---

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `! [remote rejected] ... refusing to allow ... workflow` | Token lacks `workflows` scope | Use §1 Option B (human push) or grant scope (Option A). |
| `make.sh: line ..: ./make.sh: Permission denied` | Lost executable bit | `git update-index --chmod=+x MINERVA_PID/make.sh` and commit. |
| `OSError: no library called "cairo" was found` | Cairo not installed | Ensure the **Install system dependencies** step ran; `libcairo2-dev` provides it. |
| `ERROR: expected >= 2 source SVGs in data/svg/` | Source SVGs not checked out (LFS?) | Confirm `data/svg/*.svg` are committed and pulled. |
| Golden gate fails with count drift | A code change altered statistics intentionally | Update the committed `reports/*_statistics.json` snapshot in the same PR. |
| Golden gate "no committed golden" warning | Stats file untracked | Commit the baseline `reports/*_statistics.json`; the gate then enforces it. |
| Job passes on 3.11 but fails on 3.12 | Version drift in stdlib/deps | Inspect the failing matrix log; pin/adjust the affected code. |
| pip cache miss every run | `cache-dependency-path` mismatch | Verify path is `MINERVA_PID/requirements.txt`. |

---

## 6. Definition of done (W007)

- [ ] `.github/workflows/minerva-pid-test.yml` active on `main` (§1/§2).
- [ ] Matrix green on Python 3.10 / 3.11 / 3.12.
- [ ] `./make.sh` exits 0 in CI.
- [ ] All `tests/test_*.py` pass (50 assertions).
- [ ] Golden-file gate active and tolerant of XLSX jitter.
- [ ] Build artifacts uploaded per run.
- [ ] Status badge added to README.

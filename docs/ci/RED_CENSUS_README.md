# RED census, BD ledger and launcher gate (report-only)

Status: **PROPOSAL.** Merging the PR that adds these files is the owner's
decision to make ABACUS the home of the BD (burn-down) ledger. Until then the
ledger here is a seed, not an authority.

Everything below is report-only: nothing fails a PR, nothing writes to the
repository from CI, and no workflow has `contents: write`.

| Piece | Path | Role |
|---|---|---|
| Census | `scripts/red_census.py` | Classifies every active workflow by its default-branch history |
| Ledger | `ledger/bd_ledger.jsonl` | Append-only, hash-chained BD root rows |
| Ledger verify | `scripts/red_census.py --verify-ledger` | Chain + root_id + member-uniqueness check |
| Launcher gate | `scripts/launcher_gate.py` | Flags workflow steps launching local paths that do not exist |
| Gate exceptions | `ledger/launcher_exceptions.yaml` | Owner-approved, expiring suppressions (empty) |
| Workflows | `.github/workflows/red-census.yml`, `.github/workflows/launcher-gate.yml` | Native, read-only runners |
| Tests | `tests/test_red_census.py`, `tests/test_launcher_gate.py` | Offline, inline fixtures, no network |

## 1. RED census

Inputs are native GitHub REST responses only (`actions/workflows`,
`actions/workflows/{id}/runs`, `actions/runs/{id}/jobs`, `commits`,
`contents/.github/workflows`). Pagination is an explicit `page=` loop because
Link-header pagination is unreliable behind the agent proxy.

For every **active** workflow whose path is under `.github/workflows/`, the
last 10 completed runs on the default branch (PR events excluded) are reduced
to decisive conclusions (`success` = green; `failure`, `timed_out` = red;
`cancelled`, `skipped`, `neutral`, … ignored):

| Class | Meaning |
|---|---|
| `EVERRED` | every decisive run in the window is red |
| `GREEN_TO_RED` | exactly one transition, newest red; `first_red_sha` / `first_red_run_id` = oldest red of the current streak |
| `FLAKY` | two or more red/green transitions |
| `GREEN` | all green, or recovered (one red→green transition) |
| `NO_MAIN_RUNS` | no decisive default-branch run in the window |
| `STARTUP_FAILURE` | the only failures are runs that failed **with zero jobs** (native `startup_failure`, or `failure` whose job list is empty, e.g. GitHub "Internal server error" at startup). Such runs are non-decisive everywhere; a workflow with some of them carries the `STARTUP_FAILURES` flag |
| `GHOST` | GitHub lists the workflow as active, but its path does not exist at the default-branch HEAD. Example: `dow-integration-ci-cd.yml`, deleted in #1375 (f3f6ff10, 2026-09-26), successor `dow-integration.yml` green. Reported separately, never counted as EVERRED / GREEN_TO_RED |

Flags: `STALE` when the workflow file's latest default-branch commit is newer
than its newest default-branch run (the red history may predate a fix);
`PARTIAL` (repo and report level) when a paginated API total exceeds what was
fetched; a PARTIAL census must not be promoted to a complete one.

Following `docs/ci/EVERRED_QUEUE_VIEW_README.md`: the JSON is deterministic
(sorted keys, no wall-clock timestamp; the observation time belongs in the
external evidence manifest / the run metadata), and census counts are
workflow classes, **never summed** with BD roots, queue counts, issues or job
counts. With `--ledger`, each workflow is annotated with the ledger root_ids
(and their latest state) that already cover it, so a red workflow is either
evidence for an existing root or `UNROOTED`. The census never mints IDs.

```
GITHUB_TOKEN=... python scripts/red_census.py GBOGEB/ABACUS --ledger ledger/bd_ledger.jsonl \
    --out red-census.json --summary summary.md [--record responses.json]
python scripts/red_census.py GBOGEB/ABACUS --from-json responses.json --out replay.json   # offline
```

`--record` saves every REST response keyed by `GET path?query`; `--from-json`
replays it, which is how the tests run and how a census can be re-derived
byte-for-byte.

## 2. BD ledger

`ledger/bd_ledger.jsonl`, one canonical JSON row per line:

```
{root_id, family, title, repo, workflows[], state, evidence[], [note], prev_hash, row_hash}
```

- `state` ∈ `ACTIVE`, `READY`, `HOLD`, `BLOCKED`, `BURNED`.
- `row_hash` = sha256 of the canonical JSON (sorted keys, `,`/`:` separators,
  ASCII) of the row without `row_hash`; `prev_hash` = previous `row_hash`
  (first row: 64 zeros).
- `root_id` follows the 3P rule of
  `architecture/w64/GENERIC_3PM_3PR_BURNDOWN_METHOD.yaml`:
  sha256 of canonical `{"scope": "GBOGEB", "type": "ci-root", "members": [...]}`
  where members are the **repo-qualified**, sorted, de-duplicated workflow
  paths (`GBOGEB/ABACUS:.github/workflows/ci.yml`). Repo qualification keeps
  same-named files in ABACUS and CODEX distinct.
- Append-only: a state change is a new row with the same `root_id`; the
  latest row per root wins. Rows are never edited or deleted.

**Job- and step-scoped members.** When two roots need the same workflow
file, each takes a scoped member: `<path>#<job-id>` (a whole job) or
`<path>#<job-id>/<step name>` (one step; the step's `name:` as written, matrix
legs not distinguished). Overlap rule: a whole-file member covers every job
and step of the file, a job member covers every step of that job; two
different steps, or two different jobs, do not overlap. Seed examples:

- BD-21 owns `ci.yml#test-bridge-integration/Install dependencies` and
  `cd-unified.yml#ci-ubuntu/Install dependencies`; BD-17 owns
  `ci.yml#lint-and-static-analysis/Run mypy`.
- BD-04 owns `ci-pipeline.yml#unit-tests/Run Tests` (the Windows capture
  failure fixed by #2657); BD-25 owns
  `ci-pipeline.yml#unit-tests/G family tests (ci_governance)` and
  `ci-governance.yml#policy-and-inventory`.

`--verify-ledger [PATH]` checks required fields and states, the hash chain,
each `root_id` against its members, and that no member (with the overlap rule
above) appears under two different root_ids. It exits 1 on error when run by
hand; in CI the result is only written to the step summary.

`--ledger-append ENTRY.json` is the single-writer helper: it refuses to append
to an invalid ledger or to append a row that would invalidate it. It is a
local tool for the owner-designated writer; no workflow calls it.

Seed. The chain has two parts, which also shows how the ledger is meant
to evolve:

1. Rows 1-18, the baseline from the 2026-11-09 census (ABACUS head
   `9f17ded`, CODEX head `78c4c6c`): 12 open roots (BD-16, -22, -23, -17,
   -24, -11, -12a, -12b in ABACUS; BD-15, -05, -18, -07b in CODEX), each with
   the latest default-branch run of each member as evidence, plus 6 BURNED
   rows (BD-16 GHOST `dow-integration-ci-cd.yml`, BD-01/01b, BD-04, BD-21,
   CODEX BD-08, CODEX BD-06) with their PRs. BD-16 is HOLD with 6 members.
2. Appended rows, the 2026-11-10 refresh: BD-12a BURNED (#2689), BD-21
   evidence adds #2688, BD-01/01b green-run evidence, BD-16 note "owner chose
   bridge/prune/spec, no retirement" with #2693, #2694 (dmaic-v3-cd bridged and
   pruned) and #2695 (gbogeb-abacus-integration bridged), both still waiting for
   a fresh main run, BD-24 evidence adds #2690 (PyPI floors) and open #2691
   (npm), and a new root BD-25 (ACTIVE): red since #2685 (20e144e0).

Families not given for the BURNED rows are recorded as `UNASSIGNED`.

## 3. Launcher gate

For every workflow with a `push`, `schedule` or `workflow_run` trigger, each
`run:` step is tokenized and these local launch targets are checked against
the checkout: `python <script>`, `python -m <local.module>`, `bash|sh <script>`,
`source|. <script>`, `pwsh -File <script>` / `*.ps1`, `./path` or
`dir/script.ext` invoked directly, `cd|pushd <dir>`, `pip … -r <file>`, and
`uses: ./local-action`. Findings carry the job, step, kind and resolved path,
plus `guarded` (command has a `||` fallback) and `condition` (step `if:`).

It tolerates, without findings:

- `cd` into existing dirs (tracked per step; `${{ env.X }}` resolved from
  literal workflow/job/step env; `working-directory` and `defaults.run`);
- `${{ }}` / `$VAR` targets (skipped, listed under `skipped`);
- child-repo checkouts (`actions/checkout` with `path:`), downloaded
  artifacts / caches with `path:`; a checkout of another repository *without*
  `path:` marks the rest of the job unverifiable;
- files and dirs created earlier in the job (`mkdir`, `python -m venv`,
  `git clone`, `> file` redirects);
- heredoc bodies (`python - <<'PY'`), PowerShell here-strings, multi-line
  quoted strings and multi-line bash array literals.

Known limits: shell control flow is not evaluated (a launch inside
`if [ -f x ]; then … fi` is still reported); scripts produced by earlier steps
in other ways (artifacts without `path:`, generated code, `cp`) can show as
missing; `python -m` modules are only checked from the repo root and only when
their top-level package is a local directory; matrix values and `${{ }}`
expressions other than literal `env.*` and `github.workspace` are not
expanded; files under `.github/workflows/legacy/` and subdirectories are not
scanned (GitHub does not run them).

Remedy options for a finding (the gate never retires anything):

- **bridge** — re-point the step to the live code that now carries the
  function;
- **prune** — remove the dead steps and keep the live ones;
- **spec** — keep the workflow as a target for code still to be written; it
  may be made dispatch-only **only with owner approval**.

`ledger/launcher_exceptions.yaml` holds owner-approved, expiring suppressions
(`workflow`, `reason`, `owner_decision_ref`, `expires`); an expired entry is
listed and no longer applied.

## 4. Workflows

- `red-census.yml`: daily 05:17 UTC + `workflow_dispatch`;
  `permissions: actions: read, contents: read`; census of `GBOGEB/ABACUS` with
  `GITHUB_TOKEN`; ledger verify and census tables to the step summary;
  `red-census.json` uploaded as an artifact.
- `launcher-gate.yml`: `pull_request` on `.github/workflows/**` +
  `workflow_dispatch`; `permissions: contents: read`; always exits 0; findings
  to the step summary and the `launcher-gate` artifact.

## 5. Owner decisions left open

1. **Ledger home.** Merging this PR makes ABACUS the BD ledger home; not
   merging leaves the seed as a proposal only.
2. **Gate enforce mode.** The launcher gate is report-only. Enforcing it
   (failing a PR that adds or keeps a missing launcher) is a separate
   decision, best taken after the BD-16 bridge/prune assessment.
3. **Cross-repo token.** CODEX (and other federation repos) need a token with
   `actions: read` on those repos; `GITHUB_TOKEN` only covers ABACUS. The
   seed's CODEX evidence came from a sandbox run.
4. **Ledger writer.** Who may append rows (single writer per the 3P method):
   the owner, a named agent role, or a reviewed PR per append.

## 6. DMAIC Control mapping

| DMAIC Control element | Implemented by |
|---|---|
| Control plan / what is monitored | every active workflow, last 10 default-branch runs |
| Measurement system | native REST, deterministic JSON, offline replay (`--record` / `--from-json`) |
| Reaction plan trigger | new `EVERRED` / `GREEN_TO_RED` rows marked `UNROOTED`, or a BURNED root whose workflow is red again |
| Ownership / single writer | ledger append by the designated writer only; runners attach evidence to existing root_ids |
| Audit trail | hash-chained ledger, `--verify-ledger` |
| Leading indicator | `STALE` (fix landed, not yet re-run), launcher-gate findings |
| Noise separation | `GHOST`, `STARTUP_FAILURE`, `FLAKY` reported apart from red |

QA:

    python -m pytest tests/test_red_census.py tests/test_launcher_gate.py
    python scripts/red_census.py --verify-ledger

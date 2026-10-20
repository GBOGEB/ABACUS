# CODE PURPLE / CBD — Before-push to GitHub to isolated-clone evidence

This is a source-bound testflight, not merge admission, a security waiver, or
proof that GitHub can observe developer hooks run before a push.

## SIPOC and timing

| Stage | Supplier / input | Control / output | Clock |
| --- | --- | --- | --- |
| E0 index | Git staged diff | HEAD/tree; staged and unstaged diff digests | UTC, monotonic |
| E1 pre-commit | staged developer source | Black/isort/compile/pytest receipt | per-check duration |
| E2 pre-push | committed source | broader CBD unit test receipt | same host |
| E3 GitHub checkout | exact PR head SHA (not merge SHA) | runner TestPilot parity | runner UTC + monotonic |
| E4 isolated replay | local Git fetch of exact head | fresh worktree plus identical tests | same runner |
| E5 N/N+1 comparator | E3/E4 receipts | exact source/tree/test-count differences | no clock-drift claim |
| E6 security/admission | independent CI/security owners | Safety/Bandit/A10/governance/review | UNKNOWN unless proven |

**E1/E2 developer hook receipts are not available to GitHub** unless intentionally
published. GitHub can execute E3/E4 but that does not prove E1/E2 took place.
A local isolated clone is not an independently authenticated remote GitHub
re-clone. It still tests clean-checkout reproducibility for the locally
available exact Git object.

## Installation and normal operation

Install developer dependencies with python -m pip install -r requirements-dev.txt.
Then run: pre-commit install --hook-type pre-commit --hook-type pre-push.

The existing TestPilot fast pre-commit hook remains. Two added hooks execute
the source-bound E1/E2 checks and save JSON under .testpilot/e2e/.

Manual stage commands:

    python scripts/cbd_e2e_stage.py --stage pre-commit --receipt .testpilot/e2e/pre_commit.json
    python scripts/cbd_e2e_stage.py --stage pre-push --receipt .testpilot/e2e/pre_push.json
    python scripts/cbd_e2e_stage.py --stage checkout --expected-sha HEAD_SHA --receipt .testpilot/e2e/github_checkout.json
    python scripts/cbd_e2e_stage.py --stage replay --expected-sha HEAD_SHA --receipt .testpilot/e2e/fresh_clone.json
    python scripts/cbd_e2e_stage.py --stage compare --before .testpilot/e2e/github_checkout.json --after .testpilot/e2e/fresh_clone.json --receipt .testpilot/e2e/github_clone_parity.json

Replace HEAD_SHA with the full Git commit SHA (git rev-parse HEAD). The native
TestPilot GitHub workflow binds HEAD_SHA from the pull request head, not the
synthetic pull-request merge commit. It runs in an isolated runner and
publishes its own receipt artifacts.

## Measurements and missing proof

Receipts include exact HEAD/tree identities, staged/unstaged digests, command
exit/timeout, monotonic process durations, UTC wall-time, stdout/stderr SHA256
hashes, executed pytest pass denominator and source/parity status. Raw test
logs, secrets and environment dumps are not copied.

UNKNOWN remains explicit for developer hook provenance in CI, line/branch and
changed-line coverage (not produced by this tool), cross-machine clock offset,
full security/admission state, and remote fresh-clone authentication. Separate
GitHub workflow/job/step/run-attempt linkages belong to the native #2100
attribution producer and are never silently treated as causal roots.

Full source-text/branch coverage needs a separate exact-source instrumented
coverage run, not a test-count comparison. Reproducible test counts do not
prove identical assertions or line coverage.

## Safety and stage equivalence

An E3/E4 PASS means only runner-local exact-tree and executed-test parity;
it is not evidence of P0/P1 scanner closure, branch protection, review, merge,
or historical burndown. Tests never lower the repository-wide 75% main
coverage target or 80% changed-line target. Original TestPilot and all
security/REX governance gates remain independent HOLD until attested.

Source authority: TestPilot E2E worker stacked on #2100, whose parent is
#2090; no parallel canonical BD ledger or workflow SSOT is introduced.

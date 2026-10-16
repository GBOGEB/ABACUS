# GoGREEN root leverage — Wave N0/N1 telemetry

Owner issue: https://github.com/GBOGEB/ABACUS/issues/2079

## Waves
- N0: collect exact-head PR/run/job/attempt records; never treat a job label as causal root.
- N1: compare first-red logs and contemporaneous main baseline; add source-bound root IDs only after attribution.
- N2: repair the highest-leverage proven shared root on an independent branch; re-run exact-head required checks.
- N3: count *actually* released/merged PRs and post-merge regressions, not hypothetical unblockings.

## Core metrics
- Observed PR denominator (not global open-PR denominator)
- Failed job-category overlap by unique PR
- Proven root leverage: unique PRs per evidence-backed root ID
- Unknown root PRs and coverage of attribution
- Potential unique PRs released: union of root-associated PRs, **upper bound**
- Actual merge count: externally verified main SHA; not produced by this script
- Coverage: changed-line / branch / statement with source and denominator

## Initial N0 evidence
#2070 owner screenshot: four failed categories — Code Quality Checks, Security Scanning, policy-and-inventory, Full Red Proof Summary. #2077 native runs at d4ee5a55172d5b890402d3e6602174c034f83de4 confirm these same four job categories. This is two observed PRs with four overlapping labels, **zero proven shared causal roots**. The overall open PR denominator is UNKNOWN.

## Input
JSON object with `observations` array. Each observation: `pr`, `head_sha`, `run_id`, `job_id`, `workflow`, `job`, `status`; optional `first_red_signature`, `root_id`, `root_evidence`. Use an immutable source receipt URL for `root_evidence`.

Run: `python scripts/gogreen_root_leverage.py input.json --output metrics.json`.
Test: `python -m unittest discover -s tests -p test_gogreen_root_leverage.py`.

## Limitations
Not an automated GitHub PR census, merge controller or security disposition. Potential released PRs can still have other blocking roots. All required rules, CI and review approvals remain enforced.

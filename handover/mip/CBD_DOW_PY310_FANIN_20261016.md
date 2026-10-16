# CODE PURPLE — DOW + Python 3.10 disjoint owned fan-in

- Document class: **source-bound integration receipt; not
  engineering/admission authority**
- Date: 2026-10-16 (UTC-referenced GitHub runs)
- Integration PR: [ABACUS #2066][src1] (DRAFT / HOLD)
- Main base observed: `54da377cf82a358ac97903ecde0270c975b8fcc1`
- DOW parent: [#2040][src2], exact head
  `20b49316c85a0aed1bc98fdc3b3f763628296fe1`
- Upstream dependency owner: [#2026][src3], exact head
  `884212de9cdf9b168a41d8ea254d006bc3421690`
- Integrity: `DMAIC_V3/requirements.txt` Git blob
  `0422be5af1fa9901e8f99452951deb1669ffefc1`,
  `tests/test_matplotlib_requirement_compatibility.py` Git blob
  `85fd776d65c86aa756ff7774c3a6e9bf17c637da`, both imported unchanged from
  #2026.

## Before: measured first-red and retry economics

- [ABACUS CI matrix run #5289][src4], parent #2040, source head
  `20b49316c85a0aed1bc98fdc3b3f763628296fe1`.
- Attempt 1, Python 3.10 job `116731516042`: **FAIL** in `Install tooling`.
- Attempt 2, Python 3.10 job `116977923127`: **FAIL** in the same step.
- Exact causal line:
  `No matching distribution found for matplotlib<4.0.0,>=3.11.2`. Python 3.10
  cannot install the unconditional Matplotlib 3.11.2 floor.
- Python 3.11 and Python 3.12 both **PASS** in the matrix; their jobs on
  attempt 2 were **reused from attempt 1**, not independent re-execution.
- Attempt 2 proof completeness **FAIL**, with
  `3.10:functional_compatibility:UNCLASSIFIED_SKIPPED` and
  `3.10:recursive_build:UNCLASSIFIED_SKIPPED`. Compatibility gate **FAIL**
  downstream.
- First-red reproducibility: **2 / 2** Python 3.10 attempted installs fail
  with the same root fingerprint; this measures persistence, not independent
  reliability.
- Failure amplification: **1 root** generates **3 failed job conclusions**
  (matrix Python 3.10, proof completeness, compatibility gate). Do not count
  these as 3 independent roots.
- Parent DOW + Recursive DMAIC workflow **PASS** on the original #2040 head
  (branch coverage xdist repair). It does not prove new combined head.

## Canonical repair: do not duplicate source ownership

- #2026 exact source and test blobs are imported byte-for-byte. Its
  [native run #5237][src5] passed Python 3.10 / 3.11 / 3.12, proof
  completeness and the compatibility gate on **#2026's own exact head only**.
- The imported conditional markers also constrain `pytest-asyncio` and
  `pylint` for supported older runtimes. Do not loosen security, testing,
  quality or interpreter gates to create a green status.
- This candidate integrates that one upstream dependency root with #2040's
  disjoint xdist workflow/test source, rather than creating another
  independent root patch.

## Native proof testflight and decision contract

1. On this new integration head, require actual terminal `CI - ABACUS Matrix`
   jobs: 3.10 / 3.11 / 3.12 and postmatrix proof completeness + compatibility.
2. Require `DOW + Recursive DMAIC - Enhanced CI` with exact head and inspect
   xdist/branch-mode runtime (not just a green workflow title).
3. Inspect test collections, positive and executable negative controls, stdout
   first-red, run ID, attempt, step/job clocks and artifact digests.
4. Compute the matched cohort before/after: Python environments **2/3 to
   target 3/3** (distinct from raw job counts), first-red signature
   persistence, blocked proof stages, retries/attempts, source-specific
   coverage numerator and denominator.
5. If terminal error differs, record `new_first_red` separately. If the same
   incompatible resolver persists, do not rerun blindly.
6. Preserve independent Safety, Bandit, A10, governance, reviewer, effective
   required-check and head-SHA verification. No silent waiver or direct merge.
7. Merge only via eligible independent review and governance; record postmerge
   exact main SHA and REX identity. Do not count candidate source repair as
   accepted BD root closure.

**State at receipt creation:** pending integration CI. `merge_admission=HOLD`
; `security_waiver=false`; `authority_transfer=false`;
`accepted_rex=UNKNOWN`; `accepted_root_closures=UNKNOWN`.

## Scaling interface

One source-owned root `pip:py310:matplotlib>=3.11.2:unsatisfiable` can be
linked to any failed job manifestation with its own
`repo, sha, run_id, attempt, job_id, step, timestamp`. Disjoint workers may
inspect separate jobs and report fingerprints, but **one source-owner lease**
controls the requirements-file modification. A single integration PR
recombines exact source blobs and reruns the full proof set. No worker is
independently authenticated by this document.

[src1]: https://github.com/GBOGEB/ABACUS/pull/2066
[src2]: https://github.com/GBOGEB/ABACUS/pull/2040
[src3]: https://github.com/GBOGEB/ABACUS/pull/2026
[src4]: https://github.com/GBOGEB/ABACUS/actions/runs/38825117720
[src5]: https://github.com/GBOGEB/ABACUS/actions/runs/38783468536

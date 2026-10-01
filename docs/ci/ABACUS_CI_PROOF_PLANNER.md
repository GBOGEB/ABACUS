# ABACUS CI proof planner

The ABACUS Python compatibility workflow uses a risk-based proof planner.
The planner reduces redundant pull-request execution without removing the
repository's full compatibility recertification.

## Pull-request modes

| Change class | Pull-request proof |
| --- | --- |
| Documentation or non-Python metadata | Python 3.12 sentinel |
| Ordinary Python change | Python 3.12 plus one deterministic sample |
| CI, dependency, packaging, or interpreter change | Full 3.10/3.11/3.12 |

For ordinary Python changes, the secondary compatibility sample is
deterministic. Even-numbered pull requests select Python 3.10 and odd-numbered
pull requests select Python 3.11.

## Full recertification

The complete Python 3.10, 3.11, and 3.12 matrix still runs after merge on the
configured push branches and on the scheduled compatibility run. Release or
compatibility-sensitive changes therefore retain full interpreter coverage.

## Runner control

Production compatibility jobs use the explicitly selected Ubuntu image.
A scheduled `ubuntu-latest` canary is separate from production proof so an
upcoming hosted-runner migration can be detected before the production runner
is intentionally changed.

The canary installs repository dependencies and the package fail closed, then
runs the migration-sensitive smoke proof.

## Artifact semantics

Jobs first detect whether runtime artifacts exist. If no payload was produced,
artifact upload is intentionally skipped. If a payload is detected, the upload
step treats missing files as an error instead of producing an ignorable warning.

## Stable gate

`ABACUS compatibility gate` is the stable result for the proof set selected
by the planner. The job summary records the selected proof mode and the reason
for it.

This document is intentionally a low-risk documentation-only change. Its pull
request is also used as an observable sentinel-mode proof that the planner can
reduce matrix execution while preserving the full recertification path.

# CODE PURPLE / SUT V3 — Live evidence dashboard

**Status:** additive review candidate, not a replacement of the existing default GUI or merge authority.

Open `dashboard_v3.html` directly for read-only GitHub metrics, or serve from the trusted local SUT GUI environment to use pre-existing allowlisted testflight features. The dashboard refreshes read-only GitHub data every 60 seconds, marks 120-second-old readbacks as stale and preserves UNKNOWN on failed requests.

## Measurement contracts
- Exact PR #1956-head run census, explicitly sample-bound, not proof of current-main health.
- Terminal successful-workflow fraction; failing-workflow fraction; queued+pending fraction, all with denominators.
- On-demand first-red job/step drill-down limited to five failed workflows, with pagination and source identity caveats.
- DMAIC and MIP evidence requirements; UNKNOWN when root attribution, effective policy, coverage matching or security fingerprints absent.
- PCA and Bradley-Terry buttons are **sample eligibility heuristics**, not fitting, explanation, calibration or ranking. User-entered counts are not native telemetry.
- Reverse pressure is directed graph reasoning only; no probability of technical success or physical hydraulic pressure estimate is claimed.

## Acceptance
Local HTML structure and Node JavaScript syntax: PASS. Browser visual/runtime Playwright: DEFERRED due managed Chromium `ERR_BLOCKED_BY_ADMINISTRATOR` on both local file and localhost. Native exact-head GitHub CI on this candidate: UNKNOWN until producer run completes.

No automated merge, scanner waiver, unverified coverage gain or engineering compliance credit.

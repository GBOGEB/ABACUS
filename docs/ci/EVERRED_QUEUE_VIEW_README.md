# EVERRED live queue / Code Purple integration

Canonical dashboard: docs/code_purple_execution_graph.html
Tracking: ABACUS #1877 (workflow pressure, fan-out and lossless supersession)

The live panel fetches GitHub REST queued and in-progress workflow runs, and never
infers actual runner-slot utilisation from run counts. It uses read-only requests
and keeps unknown/missing evidence explicit. A paginated first page (100 records
per state) is marked PARTIAL when API totals exceed the fetched count.

Controls: workflow search, status filter, grouped-by-workflow/trigger/status
views, UTC time display, source SHA, inline inspector and native-run link.
Colors are redundant with badge text and accessible focus indicators.

Deterministic offline producer:

    python scripts/everred_queue_snapshot.py \
      --queued queued.json --running running.json --out queue-snapshot.json

Inputs must be native GitHub Actions REST /actions/runs responses. The output
has no wall-clock timestamp: collect observation_at and exact request URLs
in the external evidence manifest. An input with a partial first page must
not be promoted to a complete census. Never sum this queue with BD roots,
issues, scanner findings, GitHub job counts or Crew assignments.

QA:

    python -m unittest tests.test_code_purple_queue_readback

This PR is an observational UI/producer improvement, not a changed security
gate, merge eligibility decision, branch rule or review waiver.

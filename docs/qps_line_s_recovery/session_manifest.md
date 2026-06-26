# Session Manifest - QPS Line S Recovery Model

## Scope

This manifest captures the current recursive build lineage for the QPS Line S recovery model and Applicant response package.

## Root intent

Answer the Applicant question for RTM-261 and RTM-292:

> What pressure build-up is allowed in Line S for recovery of 100-200 g/s, and is there a flow profile for how quickly the mass flow from Cryogenic Users builds up?

## Lineage

1. Initial helium storage calculation: 120 m3 vessel, helium at 15 barg, filling from 1 barg to 15 barg.
2. First Line S framing: recovery compressor capacity, 1 x 50 g/s and 2 x 50 g/s, with HP compressor needed for 200 g/s peak.
3. D2.1 pages 34-37 added: LOOP / loss-of-utility source basis.
4. Appendix D2.1 added: General PFD, SIMCRYOGENICS model, modes.
5. Native DOCX added: stronger parsing source for sections 5.6.5, 5.6.6, 8.2, 8.3, 8.4.
6. Reduced model created: Line S pressure-buffer model, not full SIMCRYOGENICS reproduction.
7. Corrected heat sensitivity: 8700 W is design point = true baseline x 1.44; uncertainty-only case is 7250 W.
8. Repository scaffold created in ABACUS PR #582.
9. External helper issues created for parallel workstreams.

## Current active repositories

- GBOGEB/ABACUS: domain model, traceability, Applicant-answer package.
- GBOGEB/CODEX: reusable helper tooling pattern for index, glossary, manifest, progress refresh.

## Current branch and PR

- Branch: w001
- PR: #582
- Main tracking issue: #581

## Model status

Reduced first-order model active. Full SIMCRYOGENICS reproduction deferred to later waves.

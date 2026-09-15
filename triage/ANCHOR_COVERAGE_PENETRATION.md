# Anchor coverage penetration findings

Source snapshot: GBOGEB/ABACUS@f8a5c36464866b993b6d37cfe748fe2fab3320bc

## Evidence boundaries

W104 counts were path heuristics, not verified integration coverage. Schema 2 removes directory-based linkage credit, uses anchor token boundaries, fixes version-folder recognition, retains complete candidate lists, and leaves verified linkage unknown. Historical W104 receipts are preserved, not silently restated.

## Source-read findings

- triage/RUNTIME_AGENT_REGISTRY.yaml declares DMAIC_V3/core runtime components canonical and local_mcp/agent_orchestrator_v3.0.py compatibility-active. Version naming alone is not evidence of obsolescence.
- Five matching agent filenames in local_mcp/agents and DMAIC_V3/local_mcp/agents have different Git blob SHAs: analysis_artifact_analyzer, analysis_cryo_dm, analysis_document_consumer, analysis_smoke_test, documentation_framework (all v2.3_OPTIMIZED.py). Preserve both until method-level comparison and caller tests identify unique behavior.
- DMAIC_V3/local_mcp/agents/dow_knowledge_extractor.py contains contract normalization, input/output hashing, batch extraction, recursive-hook inspection and nesting analysis. Its insights include heuristic assertions based on field presence. Treat these as observations, not validation credit.
- The extractor writes its input file and adds a current timestamp. Reuse requires explicit mutation and repeatability tests.
- .github/workflows-pending/dashboard-health.yml contains dashboard existence checks, asset-reference checks, link reporting and issue escalation. Do not activate automatically: review any active counterpart, permissions and side effects first.

## Convergence gates

1. Resolve registry declarations to existing source paths, retaining evidence provenance.
2. Trace imports, entrypoints, workflow calls and producer/consumer artifacts; distinguish declared from executable edges.
3. Compare overlapping methods, signatures, side effects and tests before selecting canonical implementations.
4. Route retained capability through KEB/DOW contracts and exercise a representative end-to-end consumer.
5. Record exact tested commit, command, result and remaining unknowns. Only then claim verified coverage.

No Git gitlinks (mode 160000) were present in the complete recursive tree at this snapshot. Embedded directories are not thereby proven independent repositories; external repository discovery and historical/deleted-branch recovery remain unperformed.

## Verification

Four focused scanner regression tests passed locally for this repository. Full repository runtime and CI were not executed. This is a scanner correction and bounded source audit, not completed semantic coverage, recovered engineering value, or DoV promotion.

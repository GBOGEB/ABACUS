# Sanitized receipt contract

## Producer summary

Required top-level fields:

- `schema_version`: currently `0.1`
- `program`: `MIP`
- `verification`: `PASS` for accepted evidence
- `repository`: repository identity
- `head_sha`: exact evaluated commit SHA
- `raw_receipt_retention`: `transient_runner_only` unless stricter authority
  says otherwise
- `root_self_index.runs`: at least `2` for repeatability proof
- `root_self_index.normalized_equal`: `true`

When a nested surface is present, also require:

- `nested_surface.path`
- `nested_surface.runs >= 2`
- `nested_surface.normalized_equal == true`

When a nested diagnostic is claimed, require:

- `nested_diagnostic.verification == PASS`
- `nested_diagnostic.parent_sha == head_sha`
- a named source contract or equivalent evidence origin
- transient raw-receipt retention

## Consumer summary

Required fields:

- `schema_version`: `0.1`
- `program`: `MIP`
- `consumer_verification`: `PASS`
- `repository`: same repository as producer
- `head_sha`: same exact SHA as producer
- `producer_artifact`: identity of the consumed producer artifact
- `checks`: non-empty list of validated predicates
- `raw_receipt_retention`: `transient_runner_only`

## Evidence classes

- `BRANCH_CAUSED`: branch introduced the failing predicate.
- `PRE_EXISTING`: equivalent predicate failed before the branch.
- `METADATA_OR_GOVERNANCE`: PR metadata, policy, or inventory failure;
  not runtime product code.
- `EXTERNAL`: service, runner, permission, or external dependency.
- `UNKNOWN`: insufficient evidence; do not infer causality.

## Promotion rule

A reusable/self-produce surface can move toward GREEN only when another
execution surface can consume it or validate it through a deterministic
contract. Presence-only discovery remains AMBER.

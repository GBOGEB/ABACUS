# QPS Cost SSOT Boundary

This directory contains only public-safe schemas, synthetic fixtures and semantic contracts.

It must not contain:

- bidder offer text or commercial values;
- confidential evidence extracts;
- supplier documents;
- generated Office/PDF/image/archive binaries;
- user-specific OneDrive paths;
- credentials or tokens.

Project-specific values belong in the private overlay repository and external evidence vault.

## Intended public-safe contents

```text
schemas/
  cost_model.schema.yaml
  evidence_registry.schema.yaml
  release_config.schema.yaml
synthetic/
  sample_offer_stage_values.csv
  sample_spare_parent_mapping.csv
semantic_contracts/
  workbook_outputs.yaml
  document_outputs.yaml
  slide_outputs.yaml
```

## Assimilation rule

An Office review change is never copied directly into this directory. It is first classified as one of:

1. data change;
2. calculation-logic change;
3. narrative change;
4. formatting-only change.

Only approved, normalized text-source changes are committed, followed by a clean rebuild and a new immutable release.

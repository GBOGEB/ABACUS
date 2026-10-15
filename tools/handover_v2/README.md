# Evidence-bound handover V2 — ABACUS pilot

This package provides a portable, **read-only** operational handover capsule.
It complements, not replaces, `scripts/handover_generator.py`,
`scripts/bd_ldab_join_census.py`, `scripts/mip_ldab_telemetry.py`,
EVERRED, Mission Control's PCA/BT consumers, and child-repository authority.

The V2 generator validates JSON Schema, source-bound ratios, first-red
dispositions, governance second-pass equality, and SHA-256 replay. It does
not authenticate GitHub credentials, launch workers, merge PRs, or certify
that a full conversation transcript has been exported.

## Prerequisites

```bash
python -m pip install -r tools/handover_v2/requirements.txt
```

## Generate / verify / diff

```bash
python tools/handover_v2/build_handover.py build --input snapshot/input.json \
  --out snapshot/capsule
python tools/handover_v2/build_handover.py verify --capsule snapshot/capsule
python tools/handover_v2/build_handover.py diff \
  --before previous/capsule --after snapshot/capsule \
  --out snapshot/delta.json
```

The input must match `handover_input.schema.json`. Supply raw evidence in
`snapshot/raw/`; **do not commit raw scanner reports or secrets**. Native
receipts must be archived with their source SHA and run/attempt identity.

The optional `wave_telemetry.py` builds a read-only, source-bound pulse
scorecard, a before/after comparison, and a federation breadth report.
Only verified V2 capsules can be consumed. Missing worker launches,
debug sessions, comparable root fingerprints, main coverage denominators,
PCA/BT inputs, and 3P* admission remain UNKNOWN/withheld.

## Governance

Adoption on ABACUS main is a separate, protected-branch PR process.
Success of the local V2 generator is **not** CI or independent approval.
The first deployment is an ABACUS-only producer; CODEX/KEB, Mission
Control/DOW and cryoplant child consumers remain in observation-only
mode until matching native inputs, method contracts and independent
review have been proved.

Do not let this tool silently override native source producers, merge
requirements, engineering authority, A10, or security checks.

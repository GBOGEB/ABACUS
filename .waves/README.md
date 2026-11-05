# Wave claims (ABACUS)

- `WAVE_CLAIMS.yaml` is **authoritative**: the CODEX roll-up reads it. It is
  seeded with participation in `QPS:W113` (receiver).
- `WAVE_CLAIMS.proposed.yaml` is a **draft only**, not read by the roll-up:
  10 rule-clean owned-wave proposals generated from this repo's records, plus
  `needs_name` (22) and `contested_ties` (16).

Promote an entry by moving it into `WAVE_CLAIMS.yaml` under `owns:`. Rename
freely within the ruleset: `W<nnn>_<SLUG>`, kebab-case aliases, and `parent`
for slug carry-forward.

Validate with `python scripts/wave_claims.py validate .waves/WAVE_CLAIMS.yaml`
(shipped with MIP kit 1.2.0).

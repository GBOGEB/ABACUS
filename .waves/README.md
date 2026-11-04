# Wave claims (ABACUS)

| File | Role |
|---|---|
| `WAVE_CLAIMS.yaml` | **Authoritative** claims of this repo, read by the CODEX roll-up. Seeded with participation in `QPS:W113` (receiver). |
| `WAVE_CLAIMS.proposed.yaml` | Draft only: 10 rule-clean owned-wave proposals generated from this repo's records, plus `needs_name` (22) and `contested_ties` (16). Not read by the roll-up. |

Promote an entry by moving it into `WAVE_CLAIMS.yaml` under `owns:`. Rename freely within the
ruleset (`W<nnn>_<SLUG>`, kebab aliases, `parent` for slug carry-forward). Validate with CODEX's
`python scripts/wave_claims.py validate .waves/WAVE_CLAIMS.yaml`.

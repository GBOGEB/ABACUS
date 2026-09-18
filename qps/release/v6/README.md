# QPS v6 ABACUS Local Preflight / Human Review Entry

Parent: `GBOGEB/cryoplant-project#1379`  
ABACUS support issue: `GBOGEB/ABACUS#1256`

ABACUS supplies analytical/runtime/review evidence and UX. It does not become QPS domain authority.

## Exact pins after administrative merge refresh

- ABACUS: `e7b2f11deac2dc9fe7b77f9622339f184a4234d2`
- QPS: `eeac2b60fc16e5b2131d4054f95da0b0c663cc40`
- CODEX: `23624e10478e115bcea2613bfcd41c24eb5dea24`

## Existing local preconfiguration

- Python: `>=3.11`; product version `5.0.0`.
- root requirements delegate to `DMAIC_V3/requirements.txt`.
- Docker: Python 3.11 service shell + health check on 8000.
- Compose: `docker-compose.yml`.
- Devcontainer: Python 3.11, GitHub CLI, Node LTS, Docker-in-Docker.
- VS Code: Python/Pylance/Black/Jupyter/Docker/YAML/GitHub Actions/Makefile integrations.
- `.vscode/settings.json`: basic type checking, formatting, pytest, YAML validation.
- `.vscode/tasks.json`: PR/CI/CD/report/test/yamllint/auth tasks.
- spell-check extension is recommended.

Observed usability/debug gaps:

- no root `.vscode/launch.json`;
- task `problemMatcher` entries are currently empty, so IDE Problems is not systematically populated;
- no root `cspell.json`;
- no root `.pre-commit-config.yaml` (a historical nested v031 file exists and is not root governance).

## QPS Offer_Eval human entry

Primary:
`docs/qps_offer_rtm_evaluation/current/DELIVERABLES_INDEX.html`

Then:

- `QPS_RTM_BT_Navigator_v22.html`
- `QPS_OFFER_Evaluation_LITE_v24.xlsx`
- `QPS_OFFER_Evaluation_FULL_v24.xlsx`
- `QPS_DMAIC_KPI_Dashboard.html`
- `PIPELINE_MAP.html`

Current artifact registry: 18 files / 15 families.

## Release-support DoD

1. freeze exact ABACUS pin for the QPS RC;
2. reproduce bounded QPS-facing runtime/support evidence on that exact pin;
3. record test counts and hashes;
4. classify referenced dashboards as current or historical;
5. return machine-readable receipt to QPS/MissionControl;
6. keep unrelated CI-governance cleanup separate and non-compensating.

Container service-shell PASS is not analytical-runtime PASS. ABACUS PASS is not QPS GOLD.

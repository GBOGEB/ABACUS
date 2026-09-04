# api/main.py — QPLANT Cryogenic Dashboard API

## Purpose
FastAPI service exposing the QPLANT physics engine (leak-rate, Monte Carlo
cost sensitivity, compressor reliability) as REST endpoints consumed by the
Next.js HBHS Engineering Portal frontend.

## Flow (ASCII)

    uvicorn api.main:app
        │
        ▼
    FastAPI app instance created (CORS middleware attached)
        │
        ├── GET  /api/v1/health ───────► cfg.reload() ─► assert SSoT sanity
        ├── GET  /api/v1/config ───────► cfg.reload() ─► ConfigSummary
        ├── GET  /api/v1/config/full ──► cfg.reload() ─► full dict dump
        ├── GET  /api/v1/config/{sec} ─► cfg.get(section)
        ├── POST /api/v1/leak-rate ────► _compute_leak_rate()
        │                                  ├─► calc_leak_rate.mbar_l_s_to_pa_m3_s()
        │                                  └─► calc_leak_rate.leak_rate_to_molar_flow_mol_s()
        ├── POST /api/v1/leak-rate/batch ─► loop over _compute_leak_rate()
        ├── POST /api/v1/monte-carlo ──► numpy RNG (seed 42) ─► triangular he_price dist
        │                                  └─► optional geopolitical disruption multiplier
        ├── POST /api/v1/compressors/reliability ─► k-of-N binomial availability (math.comb)
        ├── GET  /api/v1/compressors/specs ────► cfg.get(...)
        ├── GET  /api/v1/visualizations/catalog ► glob docs/{visualizations,visualizations_v3,plots}/*.html
        ├── GET  /api/v1/visualizations/compressor-availability ─► builds Plotly bar chart JSON
        ├── GET  /api/v1/build/status ──► reads docs/manifest.json + TRIAGE_COMPLIANCE_REPORT.json
        ├── POST /api/v1/build/trigger ─► requires X-API-Key ─► subprocess.run(["build_all.sh", ...], timeout=120)
        └── GET  / ────────────────────► service info / endpoint index

## Dependencies (local)
- api.models
- src.config_loader (ConfigLoader, cfg)
- src.calc_leak_rate
- src.monte_carlo
- src.compressor_reliability
- authentication.fastapi_middleware (verify_api_key) — guards `/api/v1/build/trigger` only

## Dependencies (external)
- fastapi, fastapi.middleware.cors, pydantic (via models)
- numpy (lazy import inside the /monte-carlo handler)
- math (lazy import inside /compressors/reliability and /visualizations/compressor-availability)

## Known failure modes (found in code, not hypothetical)
- Every endpoint catches broad `except Exception as e:` and re-raises as
  `HTTPException(500, detail=str(e))` — the raw exception message (which
  could include file paths or internal state) is returned to the HTTP
  caller. Fine for an internal engineering tool, worth revisiting before
  any public exposure.
- Config lookups (`cfg.get(...)`) fall back to hardcoded numeric defaults
  (e.g. helium price 120.0 EUR/kg, baseline leak 50.0 kg/yr, maintenance
  15000 EUR) silently on a missing key — a typo'd config path degrades
  silently to a stale default rather than failing loudly.
- CORS origins default to localhost/127.0.0.1 unless `CORS_ORIGINS` env var
  is set — fine for dev, easy to forget when deploying elsewhere.
- No guard for missing `TRIAGE_COMPLIANCE_REPORT.json` / `docs/manifest.json`
  beyond `if path.exists()` checks — degrades gracefully but returns
  `None`/`0.0` rather than surfacing "data unavailable" clearly.

## Change log
- 2026-09-04: `POST /api/v1/build/trigger` now requires a valid `X-API-Key`
  header (`dependencies=[Depends(verify_api_key)]`), reusing the existing
  `authentication` package instead of running unauthenticated. Previously
  any caller who could reach the port could trigger a build-script
  execution via `subprocess.run`.

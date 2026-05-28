# ASCII Federation Flow — GBOGEB/ABACUS (DELTA_1)

Visual reference for the DELTA_1 bi-plane federation architecture.

---

## Federation Planes

```
┌─────────────────────────────────────────────────────────────────┐
│                    DELTA_1 FEDERATION                           │
│                                                                 │
│  ┌──────────────────────────┐    ┌──────────────────────────┐  │
│  │   GOVERNANCE PLANE       │    │    RUNTIME PLANE         │  │
│  │   GBOGEB/CODEX           │◄──►│    GBOGEB/ABACUS         │  │
│  │                          │    │                          │  │
│  │  • governance            │    │  • ci_cd                 │  │
│  │  • certification         │    │  • deployment            │  │
│  │  • audit                 │    │  • runtime_validation    │  │
│  │  • operational_policy    │    │  • orchestration         │  │
│  └──────────────────────────┘    └──────────────────────────┘  │
│                                          │                      │
│                                  ┌───────▼──────────────┐      │
│                                  │   AUXILIARY PLANE    │      │
│                                  │   GBOGEB/morris.js   │      │
│                                  └──────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## CI/CD Pipeline Flow (ABACUS runtime plane)

```
  developer push
       │
       ▼
┌─────────────┐     ┌──────────────────────────────────────┐
│  GitHub      │────►│  .github/workflows/ci.yml            │
│  Actions     │     │                                      │
└─────────────┘     │  job: lint                           │
                    │    flake8 DMAIC_V3/core/…             │
                    │                                      │
                    │  job: test                           │
                    │    python -m pytest DMAIC_V3/tests   │
                    │    (90 tests, --strict-markers)       │
                    │                                      │
                    │  job: smoke                          │
                    │    pytest -m smoke                   │
                    │    scripts/verify_workflows.sh        │
                    │    python scripts/validate_docs_…     │
                    └──────────────────────────────────────┘
                                     │
                         pass        │       fail
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
           ┌────────────────┐              ┌──────────────────┐
           │ deploy-docs.yml│              │  ci-failure-debug │
           │ docs/ → Pages  │              │  -rerun.yml       │
           └────────────────┘              └──────────────────┘
```

---

## Federation Assimilation Flow

```
  recursive_build.py --smoke
         │
         ▼
  src/dmaic/federation.py::assimilate()
         │
         ├─► check federation/manifest.yaml        ✓ / ✗
         │
         ├─► check runtime/federation/
         │       codex-abacus-federation.yaml       ✓ / ✗
         │
         └─► return { status: "ok" | "degraded" | "error",
                       manifest_found: bool,
                       spec_found: bool,
                       details: [...] }
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
             status == "ok"         status != "ok"
             pytest passes          pytest fails
                    │                     │
                    ▼                     ▼
             PR open/merge         CI blocked; fix and retry
```

---

## Session Lifecycle State Machine

```
        ┌─────────┐
        │  OPEN   │◄──────────────────────────────┐
        └────┬────┘                               │
             │  iteration++                        │ reopen
             ▼                                     │
        ┌──────────┐   context limit    ┌──────────┴────────┐
        │ IN-FLIGHT │──────────────────►│   SUSPENDED       │
        └──────────┘                   │  (patch.md saved) │
             │                          └───────────────────┘
             │  all phases pass
             │  tests pass
             │  assimilate() ok
             ▼
        ┌───────────┐
        │ COMPLETED │
        └─────┬─────┘
              │  PR merged
              ▼
        ┌───────────┐
        │  ARCHIVED │
        └───────────┘
```

---

## Key File Anchors

| Symbol | File |
|--------|------|
| Federation spec | `runtime/federation/codex-abacus-federation.yaml` |
| Global manifest | `federation/manifest.yaml` |
| Python hook | `src/dmaic/federation.py` |
| Smoke tests | `DMAIC_V3/tests/test_smoke_federation.py` |
| Session lifecycle | `docs/session-lifecycle/README.md` |
| Topology narrative | `docs/FEDERATION_TOPOLOGY.md` |
| Capability matrix | `docs/CODEX_ABACUS_FEDERATION_MATRIX.md` |

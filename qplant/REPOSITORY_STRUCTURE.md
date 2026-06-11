# QPLANT Repository Structure

## Root Directory Layout

```
qplant/
├── authentication/           # API key authentication system (Phase 4)
│   ├── api_key_manager.py
│   ├── fastapi_middleware.py
│   ├── rate_limiter.py
│   ├── key_cli.py
│   ├── tests/
│   └── future_oauth2/       # OAuth2 migration prep
│
├── canonical_master/         # Parsed QPS MASTER documents (Phase 3)
│   ├── MASTER_Input_full.md
│   ├── MASTER_Input_full.html
│   ├── CONTRACT_Baseline_full.md
│   ├── CONTRACT_Baseline_full.html
│   ├── attributes/          # Structured data extraction
│   ├── slices/              # Focused views (flows, scenarios, etc.)
│   └── cross_reference.json
│
├── config_service/          # Centralized SSOT service (Phase 3)
│   ├── main.py
│   ├── validator.py
│   └── tests/
│
├── deployment/              # Kubernetes & deployment (Phase 4)
│   ├── k8s/                # 8 production manifests
│   │   ├── namespace.yaml
│   │   ├── configmap-ssot-production.yaml
│   │   ├── deployment-api-server.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   ├── hpa.yaml
│   │   └── network-policy.yaml
│   ├── scripts/
│   │   ├── deploy_production.sh
│   │   ├── validate_deployment.sh
│   │   └── rollback.sh
│   └── K8S_DEPLOYMENT_GUIDE.md
│
├── handover_dashboard/      # Main Python physics engine (Phase 1-2)
│   ├── src/
│   ├── api/                # FastAPI endpoints (14 endpoints)
│   ├── tests/
│   ├── docs/
│   └── requirements.txt
│
├── load_testing/            # Performance testing (Phase 4)
│   ├── locustfile.py
│   ├── load_test_scenarios.py
│   ├── run_load_tests.sh
│   ├── analyze_results.py
│   ├── performance_baselines.json
│   └── reports/
│
├── monitoring_dashboard/    # Real-time monitoring (Phase 2-3)
│   ├── index.html
│   ├── predictive.py
│   └── tests/
│
├── phase3_physics_validation/  # Engineering validation (Phase 3)
│   ├── calculations/
│   │   ├── flow_calculations.py
│   │   ├── heat_load_calculations.py
│   │   ├── pressure_drop.py
│   │   └── operational_scenarios.py
│   ├── engineering_baseline.json
│   └── physics_validation_report.md
│
├── sbom/                    # Software Bill of Materials (Phase 4)
│   ├── generate_sbom.py
│   ├── sbom_validation.py
│   ├── vulnerability_scan.sh
│   ├── cyclonedx_sbom.json
│   ├── spdx_sbom.json
│   └── sbom_report.md
│
├── visual_regression/       # Visual quality testing (Phase 4)
│   ├── visual_tests.py
│   ├── create_baselines.sh
│   ├── run_visual_tests.sh
│   └── baselines/
│
├── tests/                   # Project-wide integration tests
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│
├── docs/                    # Complete documentation
│   ├── phase1/
│   ├── phase2/
│   ├── phase3/
│   ├── phase4/
│   └── api/
│
├── .github/                 # GitHub configuration
│   ├── workflows/           # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
│
├── config.yaml              # Single Source of Truth (SSOT)
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container image
├── docker-compose.yml      # Local development
├── README.md               # Project overview
├── CHANGELOG.md            # Version history
├── CONTRIBUTING.md         # Contribution guidelines
├── LICENSE                 # License file
└── .gitignore
```

## Key Files by Phase

### Phase 1: Stabilization (v4.1.0)
- `config.yaml` - SSOT established
- `handover_dashboard/src/` - Physics engine
- `build_all.sh` - Unified build pipeline

### Phase 2: Integration (v4.2.0)
- `handover_dashboard/api/` - FastAPI endpoints
- `monitoring_dashboard/` - Real-time monitoring
- `cross_link_registry.json` - Dependency tracking

### Phase 3: Enterprise (v4.3.0)
- `config_service/` - Centralized config API
- `phase3_physics_validation/` - Engineering proofs
- `canonical_master/` - Parsed QPS documents
- `master_resources_validator/` - NIST/HEPAK validation

### Phase 4: Production (v4.4.0)
- `authentication/` - API key system
- `deployment/k8s/` - Kubernetes manifests
- `load_testing/` - Performance testing
- `visual_regression/` - Visual QA
- `sbom/` - Supply chain security

## Documentation Index
- Main: `README.md`
- API: `docs/api/API_DOCUMENTATION.md`
- Deployment: `PRODUCTION_DEPLOYMENT_HANDBOOK.md`
- Security: `SECURITY_DOCUMENTATION.md`
- Performance: `PERFORMANCE_BENCHMARKS.md`
- Contributing: `CONTRIBUTING.md`

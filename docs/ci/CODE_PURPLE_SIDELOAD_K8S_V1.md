# DOW W169 + W74 side-load adapter (MIP P2)

Purpose: provide a bounded **read-only producer descriptor** consumable by the CODEX KEB candidate contract and existing MissionControl Atlas, while maintaining qplant native Kubernetes ownership.

Canonical static manifests: qplant/deployment/k8s; W74 contract validator and workflow. Real API creation and workload measurement: W169 workflow using temporary kind. Without a verified exact-head run/job/attempt and actual archive hash, do not present the W169 workflow source as executed cluster success. Never emit kubeconfig, tokens, raw logs or source evidence into the public adapter.

Registry: triage/SIDELOAD_K8S_SURFACE_CURRENT_v1.json. Candidate envelope: federation/sideload/DOW_K8S_STATIC_CANDIDATE_v1.json. Existing Docker/compose products retain their own owners. This code adds no second cluster, no deployment, no second CI workflow and no new QPS engineering authority. KEB transport PR #1049 is an unmerged dependency until proven otherwise; rebind its exact SHA only after authorization and compatibility tests.

Tests: python -m pytest tests/test_dow_sideload_k8s_surface.py -q. Static native runtime proof remains governed by existing qplant validator, W74 and W169 jobs.

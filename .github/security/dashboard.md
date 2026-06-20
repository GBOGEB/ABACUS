# ABACUS Security Dashboard
> Auto-generated 2026-06-20T08:41:19Z · repo: `GBOGEB/ABACUS`  
> **2444 open alerts** across 4 tools

## Severity Overview

| Severity | Count |
|----------|------:|
| Error | 74 |
| Warning | 278 |
| Note | 2092 |

## Alerts by Tool

| Tool | Open Alerts |
|------|------------:|
| Bandit | 1793 |
| CodeQL | 492 |
| osv-scanner | 94 |
| Semgrep | 65 |

## REX Group Summary
_Groups are defined in [security.toml](security.toml)_

| REX Group | Risk | Count | Fix Priority |
|-----------|------|------:|-------------|
| 🔴 SEC_SUBPROCESS | HIGH | 94 | Fix now |
| 🔴 SEC_HARDCODED_SECRET | HIGH | 7 | Fix now |
| 🟠 SEC_WEAK_HASH | MEDIUM | 10 | Fix next sprint |
| 🟠 SEC_TEMPFILE | MEDIUM | 4 | Fix next sprint |
| 🟡 SEC_ASSERT | LOW | 1483 | Suppress / defer |
| 🟡 QUAL_DEAD_CODE | LOW | 250 | Suppress / defer |
| ⚪ OTHER | INFO | 596 | Suppress / defer |

## Hottest Files (most alerts)

| File | Alert Count |
|------|------------:|
| `DMAIC_V3/tests/test_log_monitor.py` | 60 |
| `DMAIC_V3/tests/test_super_bridge.py` | 54 |
| `MINERVA_PID/tests/test_w005_reconciliation.py` | 52 |
| `DMAIC_V3/tests/test_post_deployment_workspace_ingestion.py` | 51 |
| `tests/test_release_gate.py` | 45 |
| `requirements.txt` | 44 |
| `qplant/handover_dashboard/tests/test_api.py` | 44 |
| `DMAIC_V3/tests/test_phase1_define.py` | 43 |
| `MINERVA_PID/tests/test_w006_crossmap.py` | 41 |
| `DMAIC_V3/tests/test_phase4_improve.py` | 41 |

## Alert Detail by REX Group

### 🔴 SEC_SUBPROCESS (94 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [2476](https://github.com/GBOGEB/ABACUS/security/code-scanning/2476) | Semgrep | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_streamlined_deployment.py` | 27 | error |
| [2475](https://github.com/GBOGEB/ABACUS/security/code-scanning/2475) | Semgrep | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_comprehensive_deployment.py` | 48 | error |
| [2474](https://github.com/GBOGEB/ABACUS/security/code-scanning/2474) | Semgrep | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_cicd_roundtrip_test.py` | 48 | error |
| [2473](https://github.com/GBOGEB/ABACUS/security/code-scanning/2473) | Semgrep | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `deploy_full_integration.py` | 65 | error |
| [2012](https://github.com/GBOGEB/ABACUS/security/code-scanning/2012) | Bandit | `B602` | `cold_start_doctor.py` | 19 | error |
| [2003](https://github.com/GBOGEB/ABACUS/security/code-scanning/2003) | Bandit | `B602` | `run_streamlined_deployment.py` | 27 | error |
| [2001](https://github.com/GBOGEB/ABACUS/security/code-scanning/2001) | Bandit | `B602` | `run_comprehensive_deployment.py` | 48 | error |
| [1999](https://github.com/GBOGEB/ABACUS/security/code-scanning/1999) | Bandit | `B602` | `run_cicd_roundtrip_test.py` | 48 | error |
| [1650](https://github.com/GBOGEB/ABACUS/security/code-scanning/1650) | Bandit | `B602` | `deploy_full_integration.py` | 65 | error |
| [2579](https://github.com/GBOGEB/ABACUS/security/code-scanning/2579) | Bandit | `B603` | `golden_gate.py` | 44 | note |
| [2577](https://github.com/GBOGEB/ABACUS/security/code-scanning/2577) | Bandit | `B603` | `golden_gate.py` | 36 | note |
| [2269](https://github.com/GBOGEB/ABACUS/security/code-scanning/2269) | Bandit | `B603` | `test_github_roundtrip.py` | 117 | note |
| [2266](https://github.com/GBOGEB/ABACUS/security/code-scanning/2266) | Bandit | `B603` | `test_github_roundtrip.py` | 68 | note |
| [2263](https://github.com/GBOGEB/ABACUS/security/code-scanning/2263) | Bandit | `B603` | `test_github_roundtrip.py` | 31 | note |
| [2255](https://github.com/GBOGEB/ABACUS/security/code-scanning/2255) | Bandit | `B603` | `test_docker_images.py` | 61 | note |
| [2252](https://github.com/GBOGEB/ABACUS/security/code-scanning/2252) | Bandit | `B603` | `test_docker_images.py` | 42 | note |
| [2248](https://github.com/GBOGEB/ABACUS/security/code-scanning/2248) | Bandit | `B603` | `test_docker_images.py` | 27 | note |
| [2170](https://github.com/GBOGEB/ABACUS/security/code-scanning/2170) | Bandit | `B603` | `git_manager.py` | 64 | note |
| [2169](https://github.com/GBOGEB/ABACUS/security/code-scanning/2169) | Bandit | `B603` | `git_manager.py` | 41 | note |
| [2167](https://github.com/GBOGEB/ABACUS/security/code-scanning/2167) | Bandit | `B603` | `full_pipeline_orchestrator.py` | 454 | note |
| [2165](https://github.com/GBOGEB/ABACUS/security/code-scanning/2165) | Bandit | `B603` | `full_pipeline_orchestrator.py` | 452 | note |
| [2163](https://github.com/GBOGEB/ABACUS/security/code-scanning/2163) | Bandit | `B603` | `dow_integration_executor.py` | 191 | note |
| [2162](https://github.com/GBOGEB/ABACUS/security/code-scanning/2162) | Bandit | `B603` | `dow_integration_executor.py` | 153 | note |
| [2161](https://github.com/GBOGEB/ABACUS/security/code-scanning/2161) | Bandit | `B603` | `test_system_bridge.py` | 228 | note |
| [2155](https://github.com/GBOGEB/ABACUS/security/code-scanning/2155) | Bandit | `B603` | `workflow_analyzer.py` | 333 | note |
| [2153](https://github.com/GBOGEB/ABACUS/security/code-scanning/2153) | Bandit | `B603` | `workflow_analyzer.py` | 288 | note |
| [2151](https://github.com/GBOGEB/ABACUS/security/code-scanning/2151) | Bandit | `B603` | `workflow_analyzer.py` | 26 | note |
| [2025](https://github.com/GBOGEB/ABACUS/security/code-scanning/2025) | Bandit | `B603` | `markdown_exec_runner.py` | 29 | note |
| [2024](https://github.com/GBOGEB/ABACUS/security/code-scanning/2024) | Bandit | `B603` | `markdown_exec_runner.py` | 24 | note |
| [2018](https://github.com/GBOGEB/ABACUS/security/code-scanning/2018) | Bandit | `B603` | `fetch_workflow_errors.py` | 21 | note |
| … | _64 more — see alerts.yaml_ | | | | |

### 🔴 SEC_HARDCODED_SECRET (7 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [2171](https://github.com/GBOGEB/ABACUS/security/code-scanning/2171) | Bandit | `B105` | `log_monitor.py` | 32 | note |
| [1993](https://github.com/GBOGEB/ABACUS/security/code-scanning/1993) | Bandit | `B105` | `classify_artifacts.py` | 128 | note |
| [1988](https://github.com/GBOGEB/ABACUS/security/code-scanning/1988) | Bandit | `B105` | `analyze_repo.py` | 258 | note |
| [1918](https://github.com/GBOGEB/ABACUS/security/code-scanning/1918) | Bandit | `B105` | `collect_metrics.py` | 99 | note |
| [1611](https://github.com/GBOGEB/ABACUS/security/code-scanning/1611) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 378 | note |
| [1610](https://github.com/GBOGEB/ABACUS/security/code-scanning/1610) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 315 | note |
| [1609](https://github.com/GBOGEB/ABACUS/security/code-scanning/1609) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 164 | note |

### 🟠 SEC_WEAK_HASH (10 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [1992](https://github.com/GBOGEB/ABACUS/security/code-scanning/1992) | Bandit | `B324` | `classify_artifacts.py` | 68 | error |
| [1651](https://github.com/GBOGEB/ABACUS/security/code-scanning/1651) | Bandit | `B324` | `fast_metrics_collector.py` | 72 | error |
| [775](https://github.com/GBOGEB/ABACUS/security/code-scanning/775) | Bandit | `B324` | `phase8_todo_management.py` | 40 | error |
| [773](https://github.com/GBOGEB/ABACUS/security/code-scanning/773) | Bandit | `B324` | `phase7_action_tracking.py` | 37 | error |
| [716](https://github.com/GBOGEB/ABACUS/security/code-scanning/716) | Bandit | `B324` | `canonical_refactoring.py` | 159 | error |
| [2489](https://github.com/GBOGEB/ABACUS/security/code-scanning/2489) | Semgrep | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `fast_metrics_collector.py` | 72 | warning |
| [2488](https://github.com/GBOGEB/ABACUS/security/code-scanning/2488) | Semgrep | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `phase8_todo_management.py` | 40 | warning |
| [2487](https://github.com/GBOGEB/ABACUS/security/code-scanning/2487) | Semgrep | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `phase7_action_tracking.py` | 37 | warning |
| [2486](https://github.com/GBOGEB/ABACUS/security/code-scanning/2486) | Semgrep | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `canonical_refactoring.py` | 159 | warning |
| [2472](https://github.com/GBOGEB/ABACUS/security/code-scanning/2472) | Semgrep | `python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1` | `classify_artifacts.py` | 68 | warning |

### 🟠 SEC_TEMPFILE (4 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [1920](https://github.com/GBOGEB/ABACUS/security/code-scanning/1920) | Bandit | `B108` | `predictive.py` | 536 | warning |
| [1403](https://github.com/GBOGEB/ABACUS/security/code-scanning/1403) | Bandit | `B108` | `build_temp_gradient_pdf.py` | 140 | warning |
| [1378](https://github.com/GBOGEB/ABACUS/security/code-scanning/1378) | Bandit | `B108` | `test_twelve_cluster_orchestrator.py` | 31 | warning |
| [1373](https://github.com/GBOGEB/ABACUS/security/code-scanning/1373) | Bandit | `B108` | `test_twelve_cluster_orchestrator.py` | 21 | warning |

### 🟡 SEC_ASSERT (1483 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [2610](https://github.com/GBOGEB/ABACUS/security/code-scanning/2610) | Bandit | `B101` | `test_review_package_validation.py` | 29 | note |
| [2609](https://github.com/GBOGEB/ABACUS/security/code-scanning/2609) | Bandit | `B101` | `test_review_package_validation.py` | 23 | note |
| [2608](https://github.com/GBOGEB/ABACUS/security/code-scanning/2608) | Bandit | `B101` | `test_review_package_validation.py` | 14 | note |
| [2607](https://github.com/GBOGEB/ABACUS/security/code-scanning/2607) | Bandit | `B101` | `test_w009_commissioning.py` | 181 | note |
| [2606](https://github.com/GBOGEB/ABACUS/security/code-scanning/2606) | Bandit | `B101` | `test_w009_commissioning.py` | 171 | note |
| [2605](https://github.com/GBOGEB/ABACUS/security/code-scanning/2605) | Bandit | `B101` | `test_w009_commissioning.py` | 169 | note |
| [2604](https://github.com/GBOGEB/ABACUS/security/code-scanning/2604) | Bandit | `B101` | `test_w009_commissioning.py` | 160 | note |
| [2603](https://github.com/GBOGEB/ABACUS/security/code-scanning/2603) | Bandit | `B101` | `test_w009_commissioning.py` | 159 | note |
| [2602](https://github.com/GBOGEB/ABACUS/security/code-scanning/2602) | Bandit | `B101` | `test_w009_commissioning.py` | 157 | note |
| [2601](https://github.com/GBOGEB/ABACUS/security/code-scanning/2601) | Bandit | `B101` | `test_w009_commissioning.py` | 144 | note |
| [2600](https://github.com/GBOGEB/ABACUS/security/code-scanning/2600) | Bandit | `B101` | `test_w009_commissioning.py` | 143 | note |
| [2599](https://github.com/GBOGEB/ABACUS/security/code-scanning/2599) | Bandit | `B101` | `test_w009_commissioning.py` | 142 | note |
| [2598](https://github.com/GBOGEB/ABACUS/security/code-scanning/2598) | Bandit | `B101` | `test_w009_commissioning.py` | 141 | note |
| [2597](https://github.com/GBOGEB/ABACUS/security/code-scanning/2597) | Bandit | `B101` | `test_w009_commissioning.py` | 126 | note |
| [2596](https://github.com/GBOGEB/ABACUS/security/code-scanning/2596) | Bandit | `B101` | `test_w009_commissioning.py` | 120 | note |
| [2595](https://github.com/GBOGEB/ABACUS/security/code-scanning/2595) | Bandit | `B101` | `test_w009_commissioning.py` | 114 | note |
| [2594](https://github.com/GBOGEB/ABACUS/security/code-scanning/2594) | Bandit | `B101` | `test_w009_commissioning.py` | 107 | note |
| [2593](https://github.com/GBOGEB/ABACUS/security/code-scanning/2593) | Bandit | `B101` | `test_w009_commissioning.py` | 104 | note |
| [2592](https://github.com/GBOGEB/ABACUS/security/code-scanning/2592) | Bandit | `B101` | `test_w009_commissioning.py` | 93 | note |
| [2591](https://github.com/GBOGEB/ABACUS/security/code-scanning/2591) | Bandit | `B101` | `test_w009_commissioning.py` | 82 | note |
| [2590](https://github.com/GBOGEB/ABACUS/security/code-scanning/2590) | Bandit | `B101` | `test_w009_commissioning.py` | 81 | note |
| [2589](https://github.com/GBOGEB/ABACUS/security/code-scanning/2589) | Bandit | `B101` | `test_w009_commissioning.py` | 80 | note |
| [2588](https://github.com/GBOGEB/ABACUS/security/code-scanning/2588) | Bandit | `B101` | `test_w009_commissioning.py` | 79 | note |
| [2587](https://github.com/GBOGEB/ABACUS/security/code-scanning/2587) | Bandit | `B101` | `test_w009_commissioning.py` | 78 | note |
| [2586](https://github.com/GBOGEB/ABACUS/security/code-scanning/2586) | Bandit | `B101` | `test_w009_commissioning.py` | 72 | note |
| [2585](https://github.com/GBOGEB/ABACUS/security/code-scanning/2585) | Bandit | `B101` | `test_w009_commissioning.py` | 71 | note |
| [2584](https://github.com/GBOGEB/ABACUS/security/code-scanning/2584) | Bandit | `B101` | `test_w009_commissioning.py` | 65 | note |
| [2583](https://github.com/GBOGEB/ABACUS/security/code-scanning/2583) | Bandit | `B101` | `test_w009_commissioning.py` | 64 | note |
| [2582](https://github.com/GBOGEB/ABACUS/security/code-scanning/2582) | Bandit | `B101` | `test_w009_commissioning.py` | 52 | note |
| [2581](https://github.com/GBOGEB/ABACUS/security/code-scanning/2581) | Bandit | `B101` | `test_w009_commissioning.py` | 51 | note |
| … | _1453 more — see alerts.yaml_ | | | | |

### 🟡 QUAL_DEAD_CODE (250 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [2568](https://github.com/GBOGEB/ABACUS/security/code-scanning/2568) | CodeQL | `py/unused-local-variable` | `test_pipeline_execution_modes.py` | 182 | note |
| [2567](https://github.com/GBOGEB/ABACUS/security/code-scanning/2567) | CodeQL | `py/unused-local-variable` | `test_pipeline_execution_modes.py` | 181 | note |
| [2566](https://github.com/GBOGEB/ABACUS/security/code-scanning/2566) | CodeQL | `py/unused-import` | `workflow_analyzer.py` | 19 | note |
| [2565](https://github.com/GBOGEB/ABACUS/security/code-scanning/2565) | CodeQL | `py/unused-import` | `test_post_deployment_workspace_ingestion.py` | 9 | note |
| [2564](https://github.com/GBOGEB/ABACUS/security/code-scanning/2564) | CodeQL | `py/unused-import` | `test_post_deployment_workspace_ingestion.py` | 8 | note |
| [2563](https://github.com/GBOGEB/ABACUS/security/code-scanning/2563) | CodeQL | `py/unused-import` | `test_post_deployment_workspace_ingestion.py` | 7 | note |
| [2562](https://github.com/GBOGEB/ABACUS/security/code-scanning/2562) | CodeQL | `py/unused-import` | `test_pipeline_modes.py` | 14 | note |
| [2561](https://github.com/GBOGEB/ABACUS/security/code-scanning/2561) | CodeQL | `py/unused-import` | `test_pipeline_execution_modes.py` | 15 | note |
| [2560](https://github.com/GBOGEB/ABACUS/security/code-scanning/2560) | CodeQL | `py/unused-import` | `test_pipeline_execution_modes.py` | 10 | note |
| [2559](https://github.com/GBOGEB/ABACUS/security/code-scanning/2559) | CodeQL | `py/unused-import` | `test_pipeline_execution_modes.py` | 9 | note |
| [2558](https://github.com/GBOGEB/ABACUS/security/code-scanning/2558) | CodeQL | `py/unused-import` | `test_pipeline_execution_modes.py` | 8 | note |
| [2557](https://github.com/GBOGEB/ABACUS/security/code-scanning/2557) | CodeQL | `py/unused-import` | `test_pipeline_execution_modes.py` | 7 | note |
| [2556](https://github.com/GBOGEB/ABACUS/security/code-scanning/2556) | CodeQL | `py/unused-import` | `test_environment_setup.py` | 3 | note |
| [2555](https://github.com/GBOGEB/ABACUS/security/code-scanning/2555) | CodeQL | `py/unused-import` | `test_bridges_bidirectional.py` | 15 | note |
| [2554](https://github.com/GBOGEB/ABACUS/security/code-scanning/2554) | CodeQL | `py/unused-import` | `log_monitor.py` | 7 | note |
| [2553](https://github.com/GBOGEB/ABACUS/security/code-scanning/2553) | CodeQL | `py/unused-import` | `handover_bridge.py` | 18 | note |
| [2552](https://github.com/GBOGEB/ABACUS/security/code-scanning/2552) | CodeQL | `py/unused-import` | `handover_bridge.py` | 12 | note |
| [2551](https://github.com/GBOGEB/ABACUS/security/code-scanning/2551) | CodeQL | `py/unused-import` | `github_tracking_manager.py` | 21 | note |
| [2550](https://github.com/GBOGEB/ABACUS/security/code-scanning/2550) | CodeQL | `py/unused-import` | `dow_engine.py` | 17 | note |
| [2549](https://github.com/GBOGEB/ABACUS/security/code-scanning/2549) | CodeQL | `py/unused-import` | `dmaic_v3_engine.py` | 30 | note |
| [2548](https://github.com/GBOGEB/ABACUS/security/code-scanning/2548) | CodeQL | `py/unused-import` | `dmaic_v3_engine.py` | 25 | note |
| [2547](https://github.com/GBOGEB/ABACUS/security/code-scanning/2547) | CodeQL | `py/unused-import` | `dmaic_postdeploy.py` | 14 | note |
| [2546](https://github.com/GBOGEB/ABACUS/security/code-scanning/2546) | CodeQL | `py/unused-import` | `ci_monitor_local.py` | 17 | note |
| [2545](https://github.com/GBOGEB/ABACUS/security/code-scanning/2545) | CodeQL | `py/unused-import` | `agent_orchestrator_v3.0.py` | 18 | note |
| [2544](https://github.com/GBOGEB/ABACUS/security/code-scanning/2544) | CodeQL | `py/unused-import` | `agent_orchestrator_v3.0.py` | 14 | note |
| [544](https://github.com/GBOGEB/ABACUS/security/code-scanning/544) | CodeQL | `py/unused-import` | `dmaic_v3_engine.py` | 29 | note |
| [543](https://github.com/GBOGEB/ABACUS/security/code-scanning/543) | CodeQL | `py/unused-import` | `dmaic_v3_engine.py` | 28 | note |
| [542](https://github.com/GBOGEB/ABACUS/security/code-scanning/542) | CodeQL | `py/unused-import` | `dmaic_v3_engine.py` | 27 | note |
| [507](https://github.com/GBOGEB/ABACUS/security/code-scanning/507) | CodeQL | `py/unused-local-variable` | `test_w003_w004.py` | 36 | note |
| [506](https://github.com/GBOGEB/ABACUS/security/code-scanning/506) | CodeQL | `py/unused-local-variable` | `symbols.py` | 651 | note |
| … | _220 more — see alerts.yaml_ | | | | |

### ⚪ OTHER (596 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [2569](https://github.com/GBOGEB/ABACUS/security/code-scanning/2569) | CodeQL | `py/call/wrong-named-argument` | `test_dmaic_contract_core.py` | 38 | error |
| [2543](https://github.com/GBOGEB/ABACUS/security/code-scanning/2543) | CodeQL | `py/syntax-error` | `docker_manager.py` | 1 | error |
| [2521](https://github.com/GBOGEB/ABACUS/security/code-scanning/2521) | Semgrep | `yaml.github-actions.security.github-script-injection.github-script-injection` | `dmaic-commit-metrics.yml` | 273 | error |
| [2520](https://github.com/GBOGEB/ABACUS/security/code-scanning/2520) | Semgrep | `yaml.github-actions.security.github-script-injection.github-script-injection` | `dmaic-commit-metrics.yml` | 273 | error |
| [2519](https://github.com/GBOGEB/ABACUS/security/code-scanning/2519) | Semgrep | `yaml.github-actions.security.github-script-injection.github-script-injection` | `dmaic-commit-metrics.yml` | 273 | error |
| [2518](https://github.com/GBOGEB/ABACUS/security/code-scanning/2518) | Semgrep | `yaml.github-actions.security.github-script-injection.github-script-injection` | `dmaic-commit-metrics.yml` | 273 | error |
| [2517](https://github.com/GBOGEB/ABACUS/security/code-scanning/2517) | Semgrep | `dockerfile.security.missing-user.missing-user` | `Dockerfile` | 56 | error |
| [2516](https://github.com/GBOGEB/ABACUS/security/code-scanning/2516) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `release.yml` | 35 | error |
| [2515](https://github.com/GBOGEB/ABACUS/security/code-scanning/2515) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `dmaic-commit-metrics.yml` | 46 | error |
| [2514](https://github.com/GBOGEB/ABACUS/security/code-scanning/2514) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `release.yml` | 35 | error |
| [2513](https://github.com/GBOGEB/ABACUS/security/code-scanning/2513) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `dmaic-commit-metrics.yml` | 46 | error |
| [2512](https://github.com/GBOGEB/ABACUS/security/code-scanning/2512) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `release.yml` | 49 | error |
| [2511](https://github.com/GBOGEB/ABACUS/security/code-scanning/2511) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `release.yml` | 35 | error |
| [2510](https://github.com/GBOGEB/ABACUS/security/code-scanning/2510) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `dmaic-commit-metrics.yml` | 46 | error |
| [2509](https://github.com/GBOGEB/ABACUS/security/code-scanning/2509) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `sprint-trigger.yml` | 28 | error |
| [2508](https://github.com/GBOGEB/ABACUS/security/code-scanning/2508) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `sprint-trigger.yml` | 25 | error |
| [2507](https://github.com/GBOGEB/ABACUS/security/code-scanning/2507) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `release.yml` | 35 | error |
| [2506](https://github.com/GBOGEB/ABACUS/security/code-scanning/2506) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `main.yml` | 175 | error |
| [2505](https://github.com/GBOGEB/ABACUS/security/code-scanning/2505) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `main.yml` | 170 | error |
| [2504](https://github.com/GBOGEB/ABACUS/security/code-scanning/2504) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `gbogeb-abacus-integration-ci-cd.yml` | 551 | error |
| [2503](https://github.com/GBOGEB/ABACUS/security/code-scanning/2503) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `gbogeb-abacus-integration-ci-cd.yml` | 367 | error |
| [2502](https://github.com/GBOGEB/ABACUS/security/code-scanning/2502) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `dow-integration.yml` | 221 | error |
| [2501](https://github.com/GBOGEB/ABACUS/security/code-scanning/2501) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `dmaic-phase-execution.yml` | 12 | error |
| [2500](https://github.com/GBOGEB/ABACUS/security/code-scanning/2500) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `dmaic-commit-metrics.yml` | 46 | error |
| [2499](https://github.com/GBOGEB/ABACUS/security/code-scanning/2499) | Semgrep | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `codespace-federation.yml` | 138 | error |
| [2495](https://github.com/GBOGEB/ABACUS/security/code-scanning/2495) | Semgrep | `python.lang.security.use-defused-xml-parse.use-defused-xml-parse` | `parser.py` | 206 | error |
| [2494](https://github.com/GBOGEB/ABACUS/security/code-scanning/2494) | Semgrep | `python.lang.security.use-defused-xml-parse.use-defused-xml-parse` | `geometry.py` | 204 | error |
| [2493](https://github.com/GBOGEB/ABACUS/security/code-scanning/2493) | Semgrep | `python.lang.security.use-defused-xml-parse.use-defused-xml-parse` | `build_atlas_v6.py` | 96 | error |
| [2492](https://github.com/GBOGEB/ABACUS/security/code-scanning/2492) | Semgrep | `python.lang.security.use-defused-xml-parse.use-defused-xml-parse` | `segment_pid.py` | 228 | error |
| [2491](https://github.com/GBOGEB/ABACUS/security/code-scanning/2491) | Semgrep | `python.lang.security.use-defused-xml-parse.use-defused-xml-parse` | `svg_extract.py` | 195 | error |
| … | _566 more — see alerts.yaml_ | | | | |

## Quick-Win Fix Order

| Priority | REX Group | Est. Alerts | Action |
|----------|-----------|------------:|--------|
| 1 | SEC_SUBPROCESS | 94 live / ~40 est. | Add `# noqa: S603` — all calls use list-form args |
| 2 | SEC_PATH_TRAVERSAL | 0 live / ~20 est. | `pathlib.Path(p).resolve(); assert is_relative_to(BASE)` |
| 3 | SEC_COMPILE_EXEC | 0 live / ~10 est. | Replace `compile+exec` with `ast.parse()` (syntax-only) |
| 4 | SEC_TEMPFILE | 4 live / ~15 est. | Remove `delete=False` from `NamedTemporaryFile` |
| 5 | SEC_ASSERT | 1483 live / ~10 est. | Add `# noqa: S101` in pytest files, raise in prod |
| 6 | QUAL_DEAD_CODE | 250 live / ~30 est. | `ruff check --fix --select F401,F841 DMAIC_V3/` |

_Dashboard last updated: 2026-06-20T08:41:19Z_
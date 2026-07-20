# ABACUS Security Dashboard
> Auto-generated 2026-07-20T07:20:13Z · repo: `GBOGEB/ABACUS`  
> **2393 open alerts** across 3 tools

## Severity Overview

| Severity | Count |
|----------|------:|
| Error | 74 |
| Warning | 184 |
| Note | 2135 |

## Alerts by Tool

| Tool | Open Alerts |
|------|------------:|
| Bandit | 1843 |
| CodeQL | 485 |
| Semgrep | 65 |

## REX Group Summary
_Groups are defined in [security.toml](security.toml)_

| REX Group | Risk | Count | Fix Priority |
|-----------|------|------:|-------------|
| 🔴 SEC_SUBPROCESS | HIGH | 95 | Fix now |
| 🔴 SEC_HARDCODED_SECRET | HIGH | 7 | Fix now |
| 🟠 SEC_WEAK_HASH | MEDIUM | 10 | Fix next sprint |
| 🟠 SEC_TEMPFILE | MEDIUM | 4 | Fix next sprint |
| 🟡 SEC_ASSERT | LOW | 1531 | Suppress / defer |
| 🟡 QUAL_DEAD_CODE | LOW | 243 | Suppress / defer |
| ⚪ OTHER | INFO | 503 | Suppress / defer |

## Hottest Files (most alerts)

| File | Alert Count |
|------|------------:|
| `DMAIC_V3/tests/test_log_monitor.py` | 60 |
| `DMAIC_V3/tests/test_super_bridge.py` | 54 |
| `MINERVA_PID/tests/test_w005_reconciliation.py` | 52 |
| `DMAIC_V3/tests/test_post_deployment_workspace_ingestion.py` | 51 |
| `tests/test_release_gate.py` | 45 |
| `qplant/handover_dashboard/tests/test_api.py` | 44 |
| `DMAIC_V3/tests/test_phase1_define.py` | 43 |
| `MINERVA_PID/tests/test_w006_crossmap.py` | 41 |
| `DMAIC_V3/tests/test_phase4_improve.py` | 41 |
| `DMAIC_V3/tests/test_bridges_bidirectional.py` | 40 |

## Alert Detail by REX Group

### 🔴 SEC_SUBPROCESS (95 alerts)

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
| [2638](https://github.com/GBOGEB/ABACUS/security/code-scanning/2638) | Bandit | `B603` | `rfi_package.py` | 57 | note |
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
| [2167](https://github.com/GBOGEB/ABACUS/security/code-scanning/2167) | Bandit | `B603` | `full_pipeline_orchestrator.py` | 453 | note |
| [2165](https://github.com/GBOGEB/ABACUS/security/code-scanning/2165) | Bandit | `B603` | `full_pipeline_orchestrator.py` | 451 | note |
| [2163](https://github.com/GBOGEB/ABACUS/security/code-scanning/2163) | Bandit | `B603` | `dow_integration_executor.py` | 190 | note |
| [2162](https://github.com/GBOGEB/ABACUS/security/code-scanning/2162) | Bandit | `B603` | `dow_integration_executor.py` | 152 | note |
| [2161](https://github.com/GBOGEB/ABACUS/security/code-scanning/2161) | Bandit | `B603` | `test_system_bridge.py` | 228 | note |
| [2155](https://github.com/GBOGEB/ABACUS/security/code-scanning/2155) | Bandit | `B603` | `workflow_analyzer.py` | 333 | note |
| [2153](https://github.com/GBOGEB/ABACUS/security/code-scanning/2153) | Bandit | `B603` | `workflow_analyzer.py` | 288 | note |
| [2151](https://github.com/GBOGEB/ABACUS/security/code-scanning/2151) | Bandit | `B603` | `workflow_analyzer.py` | 26 | note |
| [2025](https://github.com/GBOGEB/ABACUS/security/code-scanning/2025) | Bandit | `B603` | `markdown_exec_runner.py` | 29 | note |
| [2024](https://github.com/GBOGEB/ABACUS/security/code-scanning/2024) | Bandit | `B603` | `markdown_exec_runner.py` | 24 | note |
| … | _65 more — see alerts.yaml_ | | | | |

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

### 🟡 SEC_ASSERT (1531 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [2666](https://github.com/GBOGEB/ABACUS/security/code-scanning/2666) | Bandit | `B101` | `test_loop_transient.py` | 99 | note |
| [2665](https://github.com/GBOGEB/ABACUS/security/code-scanning/2665) | Bandit | `B101` | `test_loop_transient.py` | 91 | note |
| [2664](https://github.com/GBOGEB/ABACUS/security/code-scanning/2664) | Bandit | `B101` | `test_loop_transient.py` | 83 | note |
| [2663](https://github.com/GBOGEB/ABACUS/security/code-scanning/2663) | Bandit | `B101` | `test_loop_transient.py` | 75 | note |
| [2662](https://github.com/GBOGEB/ABACUS/security/code-scanning/2662) | Bandit | `B101` | `test_loop_transient.py` | 65 | note |
| [2661](https://github.com/GBOGEB/ABACUS/security/code-scanning/2661) | Bandit | `B101` | `test_loop_transient.py` | 59 | note |
| [2660](https://github.com/GBOGEB/ABACUS/security/code-scanning/2660) | Bandit | `B101` | `test_loop_transient.py` | 53 | note |
| [2659](https://github.com/GBOGEB/ABACUS/security/code-scanning/2659) | Bandit | `B101` | `test_loop_transient.py` | 52 | note |
| [2658](https://github.com/GBOGEB/ABACUS/security/code-scanning/2658) | Bandit | `B101` | `test_loop_transient.py` | 51 | note |
| [2657](https://github.com/GBOGEB/ABACUS/security/code-scanning/2657) | Bandit | `B101` | `test_loop_transient.py` | 43 | note |
| [2656](https://github.com/GBOGEB/ABACUS/security/code-scanning/2656) | Bandit | `B101` | `test_loop_transient.py` | 37 | note |
| [2655](https://github.com/GBOGEB/ABACUS/security/code-scanning/2655) | Bandit | `B101` | `test_loop_transient.py` | 33 | note |
| [2654](https://github.com/GBOGEB/ABACUS/security/code-scanning/2654) | Bandit | `B101` | `test_loop_transient.py` | 26 | note |
| [2653](https://github.com/GBOGEB/ABACUS/security/code-scanning/2653) | Bandit | `B101` | `test_loop_transient.py` | 20 | note |
| [2652](https://github.com/GBOGEB/ABACUS/security/code-scanning/2652) | Bandit | `B101` | `test_loop_transient.py` | 15 | note |
| [2649](https://github.com/GBOGEB/ABACUS/security/code-scanning/2649) | Bandit | `B101` | `test_runtime.py` | 126 | note |
| [2648](https://github.com/GBOGEB/ABACUS/security/code-scanning/2648) | Bandit | `B101` | `test_runtime.py` | 125 | note |
| [2647](https://github.com/GBOGEB/ABACUS/security/code-scanning/2647) | Bandit | `B101` | `test_runtime.py` | 124 | note |
| [2646](https://github.com/GBOGEB/ABACUS/security/code-scanning/2646) | Bandit | `B101` | `test_runtime.py` | 115 | note |
| [2645](https://github.com/GBOGEB/ABACUS/security/code-scanning/2645) | Bandit | `B101` | `test_runtime.py` | 114 | note |
| [2644](https://github.com/GBOGEB/ABACUS/security/code-scanning/2644) | Bandit | `B101` | `test_runtime.py` | 111 | note |
| [2643](https://github.com/GBOGEB/ABACUS/security/code-scanning/2643) | Bandit | `B101` | `test_runtime.py` | 110 | note |
| [2642](https://github.com/GBOGEB/ABACUS/security/code-scanning/2642) | Bandit | `B101` | `test_runtime.py` | 109 | note |
| [2641](https://github.com/GBOGEB/ABACUS/security/code-scanning/2641) | Bandit | `B101` | `test_runtime.py` | 108 | note |
| [2640](https://github.com/GBOGEB/ABACUS/security/code-scanning/2640) | Bandit | `B101` | `test_runtime.py` | 107 | note |
| [2639](https://github.com/GBOGEB/ABACUS/security/code-scanning/2639) | Bandit | `B101` | `test_runtime.py` | 106 | note |
| [2634](https://github.com/GBOGEB/ABACUS/security/code-scanning/2634) | Bandit | `B101` | `test_runtime.py` | 113 | note |
| [2633](https://github.com/GBOGEB/ABACUS/security/code-scanning/2633) | Bandit | `B101` | `test_runtime.py` | 112 | note |
| [2632](https://github.com/GBOGEB/ABACUS/security/code-scanning/2632) | Bandit | `B101` | `test_runtime.py` | 91 | note |
| [2631](https://github.com/GBOGEB/ABACUS/security/code-scanning/2631) | Bandit | `B101` | `test_runtime.py` | 73 | note |
| … | _1501 more — see alerts.yaml_ | | | | |

### 🟡 QUAL_DEAD_CODE (243 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [2651](https://github.com/GBOGEB/ABACUS/security/code-scanning/2651) | CodeQL | `py/unused-import` | `populate_package.py` | 16 | note |
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
| … | _213 more — see alerts.yaml_ | | | | |

### ⚪ OTHER (503 alerts)

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
| … | _473 more — see alerts.yaml_ | | | | |

## Quick-Win Fix Order

| Priority | REX Group | Est. Alerts | Action |
|----------|-----------|------------:|--------|
| 1 | SEC_SUBPROCESS | 95 live / ~40 est. | Add `# noqa: S603` — all calls use list-form args |
| 2 | SEC_PATH_TRAVERSAL | 0 live / ~20 est. | `pathlib.Path(p).resolve(); assert is_relative_to(BASE)` |
| 3 | SEC_COMPILE_EXEC | 0 live / ~10 est. | Replace `compile+exec` with `ast.parse()` (syntax-only) |
| 4 | SEC_TEMPFILE | 4 live / ~15 est. | Remove `delete=False` from `NamedTemporaryFile` |
| 5 | SEC_ASSERT | 1531 live / ~10 est. | Add `# noqa: S101` in pytest files, raise in prod |
| 6 | QUAL_DEAD_CODE | 243 live / ~30 est. | `ruff check --fix --select F401,F841 DMAIC_V3/` |

_Dashboard last updated: 2026-07-20T07:20:13Z_
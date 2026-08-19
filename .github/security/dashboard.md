# ABACUS Security Dashboard
> Auto-generated 2026-08-19T16:46:06Z · repo: `GBOGEB/ABACUS`  
> **2456 open alerts** across 3 tools

## Severity Overview

| Severity | Count |
|----------|------:|
| Error | 74 |
| Warning | 212 |
| Note | 2170 |

## Alerts by Tool

| Tool | Open Alerts |
|------|------------:|
| Bandit | 1906 |
| CodeQL | 485 |
| Semgrep | 65 |

## REX Group Summary
_Groups are defined in [security.toml](security.toml)_

| REX Group | Risk | Count | Fix Priority |
|-----------|------|------:|-------------|
| 🔴 SEC_SUBPROCESS | HIGH | 98 | Fix now |
| 🔴 SEC_HARDCODED_SECRET | HIGH | 7 | Fix now |
| 🟠 SEC_TEMPFILE | MEDIUM | 32 | Fix next sprint |
| 🟠 SEC_WEAK_HASH | MEDIUM | 10 | Fix next sprint |
| 🟡 SEC_ASSERT | LOW | 1552 | Suppress / defer |
| 🟡 QUAL_DEAD_CODE | LOW | 243 | Suppress / defer |
| ⚪ OTHER | INFO | 514 | Suppress / defer |

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
| `DMAIC_V3/tests/test_phase2_measure.py` | 40 |

## Alert Detail by REX Group

### 🔴 SEC_SUBPROCESS (98 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [4316](https://github.com/GBOGEB/ABACUS/security/code-scanning/4316) | Bandit | `B602` | `cold_start_doctor.py` | 19 | error |
| [4307](https://github.com/GBOGEB/ABACUS/security/code-scanning/4307) | Bandit | `B602` | `run_streamlined_deployment.py` | 27 | error |
| [4305](https://github.com/GBOGEB/ABACUS/security/code-scanning/4305) | Bandit | `B602` | `run_comprehensive_deployment.py` | 46 | error |
| [4303](https://github.com/GBOGEB/ABACUS/security/code-scanning/4303) | Bandit | `B602` | `run_cicd_roundtrip_test.py` | 46 | error |
| [3950](https://github.com/GBOGEB/ABACUS/security/code-scanning/3950) | Bandit | `B602` | `deploy_full_integration.py` | 63 | error |
| [2476](https://github.com/GBOGEB/ABACUS/security/code-scanning/2476) | Semgrep | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_streamlined_deployment.py` | 27 | error |
| [2475](https://github.com/GBOGEB/ABACUS/security/code-scanning/2475) | Semgrep | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_comprehensive_deployment.py` | 48 | error |
| [2474](https://github.com/GBOGEB/ABACUS/security/code-scanning/2474) | Semgrep | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_cicd_roundtrip_test.py` | 48 | error |
| [2473](https://github.com/GBOGEB/ABACUS/security/code-scanning/2473) | Semgrep | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `deploy_full_integration.py` | 65 | error |
| [4575](https://github.com/GBOGEB/ABACUS/security/code-scanning/4575) | Bandit | `B603` | `gen_kpi_dashboard.py` | 117 | note |
| [4573](https://github.com/GBOGEB/ABACUS/security/code-scanning/4573) | Bandit | `B603` | `gen_kpi_dashboard.py` | 112 | note |
| [4532](https://github.com/GBOGEB/ABACUS/security/code-scanning/4532) | Bandit | `B603` | `build_handover_package.py` | 98 | note |
| [4508](https://github.com/GBOGEB/ABACUS/security/code-scanning/4508) | Bandit | `B603` | `workflow_analyzer.py` | 333 | note |
| [4505](https://github.com/GBOGEB/ABACUS/security/code-scanning/4505) | Bandit | `B603` | `workflow_analyzer.py` | 288 | note |
| [4503](https://github.com/GBOGEB/ABACUS/security/code-scanning/4503) | Bandit | `B603` | `workflow_analyzer.py` | 26 | note |
| [4329](https://github.com/GBOGEB/ABACUS/security/code-scanning/4329) | Bandit | `B603` | `markdown_exec_runner.py` | 29 | note |
| [4328](https://github.com/GBOGEB/ABACUS/security/code-scanning/4328) | Bandit | `B603` | `markdown_exec_runner.py` | 24 | note |
| [4322](https://github.com/GBOGEB/ABACUS/security/code-scanning/4322) | Bandit | `B603` | `fetch_workflow_errors.py` | 21 | note |
| [4318](https://github.com/GBOGEB/ABACUS/security/code-scanning/4318) | Bandit | `B603` | `deploy_v23_github.py` | 39 | note |
| [4314](https://github.com/GBOGEB/ABACUS/security/code-scanning/4314) | Bandit | `B603` | `code_health_check.py` | 22 | note |
| [4311](https://github.com/GBOGEB/ABACUS/security/code-scanning/4311) | Bandit | `B603` | `build_book.py` | 105 | note |
| [4310](https://github.com/GBOGEB/ABACUS/security/code-scanning/4310) | Bandit | `B603` | `build_book.py` | 83 | note |
| [4309](https://github.com/GBOGEB/ABACUS/security/code-scanning/4309) | Bandit | `B603` | `build_book.py` | 58 | note |
| [4301](https://github.com/GBOGEB/ABACUS/security/code-scanning/4301) | Bandit | `B603` | `generate_lineage.py` | 176 | note |
| [4300](https://github.com/GBOGEB/ABACUS/security/code-scanning/4300) | Bandit | `B603` | `generate_lineage.py` | 41 | note |
| [4295](https://github.com/GBOGEB/ABACUS/security/code-scanning/4295) | Bandit | `B603` | `classify_artifacts.py` | 56 | note |
| [4291](https://github.com/GBOGEB/ABACUS/security/code-scanning/4291) | Bandit | `B603` | `analyze_repo.py` | 85 | note |
| [4284](https://github.com/GBOGEB/ABACUS/security/code-scanning/4284) | Bandit | `B603` | `vulnerability_scan.py` | 24 | note |
| [4282](https://github.com/GBOGEB/ABACUS/security/code-scanning/4282) | Bandit | `B603` | `generate_sbom.py` | 105 | note |
| [4280](https://github.com/GBOGEB/ABACUS/security/code-scanning/4280) | Bandit | `B603` | `generate_sbom.py` | 45 | note |
| … | _68 more — see alerts.yaml_ | | | | |

### 🔴 SEC_HARDCODED_SECRET (7 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [4297](https://github.com/GBOGEB/ABACUS/security/code-scanning/4297) | Bandit | `B105` | `classify_artifacts.py` | 128 | note |
| [4292](https://github.com/GBOGEB/ABACUS/security/code-scanning/4292) | Bandit | `B105` | `analyze_repo.py` | 258 | note |
| [4221](https://github.com/GBOGEB/ABACUS/security/code-scanning/4221) | Bandit | `B105` | `collect_metrics.py` | 99 | note |
| [3911](https://github.com/GBOGEB/ABACUS/security/code-scanning/3911) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 374 | note |
| [3910](https://github.com/GBOGEB/ABACUS/security/code-scanning/3910) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 313 | note |
| [3909](https://github.com/GBOGEB/ABACUS/security/code-scanning/3909) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 159 | note |
| [2747](https://github.com/GBOGEB/ABACUS/security/code-scanning/2747) | Bandit | `B105` | `log_monitor.py` | 28 | note |

### 🟠 SEC_TEMPFILE (32 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [4570](https://github.com/GBOGEB/ABACUS/security/code-scanning/4570) | Bandit | `B108` | `export_nav_data.py` | 14 | warning |
| [4568](https://github.com/GBOGEB/ABACUS/security/code-scanning/4568) | Bandit | `B108` | `pca_pareto_cluster.py` | 179 | warning |
| [4562](https://github.com/GBOGEB/ABACUS/security/code-scanning/4562) | Bandit | `B108` | `infer_clusters.py` | 120 | warning |
| [4561](https://github.com/GBOGEB/ABACUS/security/code-scanning/4561) | Bandit | `B108` | `infer_clusters.py` | 28 | warning |
| [4560](https://github.com/GBOGEB/ABACUS/security/code-scanning/4560) | Bandit | `B108` | `gen_kpi_dashboard.py` | 249 | warning |
| [4553](https://github.com/GBOGEB/ABACUS/security/code-scanning/4553) | Bandit | `B108` | `classify_all_rtms.py` | 170 | warning |
| [4552](https://github.com/GBOGEB/ABACUS/security/code-scanning/4552) | Bandit | `B108` | `build_workbook_v7.py` | 19 | warning |
| [4551](https://github.com/GBOGEB/ABACUS/security/code-scanning/4551) | Bandit | `B108` | `build_workbook_v7.py` | 18 | warning |
| [4550](https://github.com/GBOGEB/ABACUS/security/code-scanning/4550) | Bandit | `B108` | `build_workbook_v6.py` | 729 | warning |
| [4549](https://github.com/GBOGEB/ABACUS/security/code-scanning/4549) | Bandit | `B108` | `build_workbook_v6.py` | 652 | warning |
| [4548](https://github.com/GBOGEB/ABACUS/security/code-scanning/4548) | Bandit | `B108` | `build_workbook_v6.py` | 611 | warning |
| [4547](https://github.com/GBOGEB/ABACUS/security/code-scanning/4547) | Bandit | `B108` | `build_workbook_v6.py` | 521 | warning |
| [4546](https://github.com/GBOGEB/ABACUS/security/code-scanning/4546) | Bandit | `B108` | `build_workbook_v6.py` | 480 | warning |
| [4545](https://github.com/GBOGEB/ABACUS/security/code-scanning/4545) | Bandit | `B108` | `build_workbook_v6.py` | 448 | warning |
| [4544](https://github.com/GBOGEB/ABACUS/security/code-scanning/4544) | Bandit | `B108` | `build_workbook_v6.py` | 318 | warning |
| [4543](https://github.com/GBOGEB/ABACUS/security/code-scanning/4543) | Bandit | `B108` | `build_workbook_v6.py` | 249 | warning |
| [4542](https://github.com/GBOGEB/ABACUS/security/code-scanning/4542) | Bandit | `B108` | `build_workbook_v6.py` | 245 | warning |
| [4541](https://github.com/GBOGEB/ABACUS/security/code-scanning/4541) | Bandit | `B108` | `build_workbook_v6.py` | 99 | warning |
| [4537](https://github.com/GBOGEB/ABACUS/security/code-scanning/4537) | Bandit | `B108` | `build_workbook_v20.py` | 563 | warning |
| [4534](https://github.com/GBOGEB/ABACUS/security/code-scanning/4534) | Bandit | `B108` | `build_pdf_export.py` | 24 | warning |
| [4533](https://github.com/GBOGEB/ABACUS/security/code-scanning/4533) | Bandit | `B108` | `build_kpi_dashboard_html.py` | 3 | warning |
| [4529](https://github.com/GBOGEB/ABACUS/security/code-scanning/4529) | Bandit | `B108` | `build_handover_package.py` | 23 | warning |
| [4520](https://github.com/GBOGEB/ABACUS/security/code-scanning/4520) | Bandit | `B108` | `build_bt_deck_v6.py` | 216 | warning |
| [4519](https://github.com/GBOGEB/ABACUS/security/code-scanning/4519) | Bandit | `B108` | `build_bt_deck_v6.py` | 204 | warning |
| [4518](https://github.com/GBOGEB/ABACUS/security/code-scanning/4518) | Bandit | `B108` | `build_bt_deck_v6.py` | 169 | warning |
| [4517](https://github.com/GBOGEB/ABACUS/security/code-scanning/4517) | Bandit | `B108` | `build_bt_deck_v6.py` | 157 | warning |
| [4512](https://github.com/GBOGEB/ABACUS/security/code-scanning/4512) | Bandit | `B108` | `build_bt_deck_v12.py` | 48 | warning |
| [4510](https://github.com/GBOGEB/ABACUS/security/code-scanning/4510) | Bandit | `B108` | `build_bt_deck_v10.py` | 31 | warning |
| [4223](https://github.com/GBOGEB/ABACUS/security/code-scanning/4223) | Bandit | `B108` | `predictive.py` | 536 | warning |
| [3675](https://github.com/GBOGEB/ABACUS/security/code-scanning/3675) | Bandit | `B108` | `build_temp_gradient_pdf.py` | 140 | warning |
| … | _2 more — see alerts.yaml_ | | | | |

### 🟠 SEC_WEAK_HASH (10 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [4296](https://github.com/GBOGEB/ABACUS/security/code-scanning/4296) | Bandit | `B324` | `classify_artifacts.py` | 68 | error |
| [3951](https://github.com/GBOGEB/ABACUS/security/code-scanning/3951) | Bandit | `B324` | `fast_metrics_collector.py` | 72 | error |
| [2759](https://github.com/GBOGEB/ABACUS/security/code-scanning/2759) | Bandit | `B324` | `phase8_todo_management.py` | 40 | error |
| [2757](https://github.com/GBOGEB/ABACUS/security/code-scanning/2757) | Bandit | `B324` | `phase7_action_tracking.py` | 37 | error |
| [2704](https://github.com/GBOGEB/ABACUS/security/code-scanning/2704) | Bandit | `B324` | `canonical_refactoring.py` | 159 | error |
| [2489](https://github.com/GBOGEB/ABACUS/security/code-scanning/2489) | Semgrep | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `fast_metrics_collector.py` | 72 | warning |
| [2488](https://github.com/GBOGEB/ABACUS/security/code-scanning/2488) | Semgrep | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `phase8_todo_management.py` | 40 | warning |
| [2487](https://github.com/GBOGEB/ABACUS/security/code-scanning/2487) | Semgrep | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `phase7_action_tracking.py` | 37 | warning |
| [2486](https://github.com/GBOGEB/ABACUS/security/code-scanning/2486) | Semgrep | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `canonical_refactoring.py` | 159 | warning |
| [2472](https://github.com/GBOGEB/ABACUS/security/code-scanning/2472) | Semgrep | `python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1` | `classify_artifacts.py` | 68 | warning |

### 🟡 SEC_ASSERT (1552 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [4582](https://github.com/GBOGEB/ABACUS/security/code-scanning/4582) | Bandit | `B101` | `qa_nav_v24.py` | 66 | note |
| [4581](https://github.com/GBOGEB/ABACUS/security/code-scanning/4581) | Bandit | `B101` | `qa_nav_v24.py` | 50 | note |
| [4580](https://github.com/GBOGEB/ABACUS/security/code-scanning/4580) | Bandit | `B101` | `qa_nav_v24.py` | 46 | note |
| [4579](https://github.com/GBOGEB/ABACUS/security/code-scanning/4579) | Bandit | `B101` | `qa_nav_v24.py` | 44 | note |
| [4578](https://github.com/GBOGEB/ABACUS/security/code-scanning/4578) | Bandit | `B101` | `qa_nav_v24.py` | 36 | note |
| [4577](https://github.com/GBOGEB/ABACUS/security/code-scanning/4577) | Bandit | `B101` | `qa_nav_v24.py` | 30 | note |
| [4576](https://github.com/GBOGEB/ABACUS/security/code-scanning/4576) | Bandit | `B101` | `qa_nav_v24.py` | 25 | note |
| [4569](https://github.com/GBOGEB/ABACUS/security/code-scanning/4569) | Bandit | `B101` | `t0_taxonomy.py` | 161 | note |
| [4563](https://github.com/GBOGEB/ABACUS/security/code-scanning/4563) | Bandit | `B101` | `make_energy_pie.py` | 13 | note |
| [4556](https://github.com/GBOGEB/ABACUS/security/code-scanning/4556) | Bandit | `B101` | `fix_pdf_page_numbers.py` | 34 | note |
| [4540](https://github.com/GBOGEB/ABACUS/security/code-scanning/4540) | Bandit | `B101` | `build_workbook_v23.py` | 55 | note |
| [4539](https://github.com/GBOGEB/ABACUS/security/code-scanning/4539) | Bandit | `B101` | `build_workbook_v22.py` | 58 | note |
| [4528](https://github.com/GBOGEB/ABACUS/security/code-scanning/4528) | Bandit | `B101` | `build_deck4.py` | 61 | note |
| [4527](https://github.com/GBOGEB/ABACUS/security/code-scanning/4527) | Bandit | `B101` | `build_deck4.py` | 55 | note |
| [4526](https://github.com/GBOGEB/ABACUS/security/code-scanning/4526) | Bandit | `B101` | `build_deck3.py` | 577 | note |
| [4525](https://github.com/GBOGEB/ABACUS/security/code-scanning/4525) | Bandit | `B101` | `build_deck3.py` | 570 | note |
| [4524](https://github.com/GBOGEB/ABACUS/security/code-scanning/4524) | Bandit | `B101` | `build_deck3.py` | 243 | note |
| [4516](https://github.com/GBOGEB/ABACUS/security/code-scanning/4516) | Bandit | `B101` | `build_bt_deck_v6.py` | 79 | note |
| [4514](https://github.com/GBOGEB/ABACUS/security/code-scanning/4514) | Bandit | `B101` | `build_bt_deck_v12.py` | 151 | note |
| [4513](https://github.com/GBOGEB/ABACUS/security/code-scanning/4513) | Bandit | `B101` | `build_bt_deck_v12.py` | 102 | note |
| [4511](https://github.com/GBOGEB/ABACUS/security/code-scanning/4511) | Bandit | `B101` | `build_bt_deck_v10.py` | 64 | note |
| [4500](https://github.com/GBOGEB/ABACUS/security/code-scanning/4500) | Bandit | `B101` | `test_schema_validation.py` | 25 | note |
| [4499](https://github.com/GBOGEB/ABACUS/security/code-scanning/4499) | Bandit | `B101` | `test_schema_validation.py` | 24 | note |
| [4498](https://github.com/GBOGEB/ABACUS/security/code-scanning/4498) | Bandit | `B101` | `test_schema_validation.py` | 19 | note |
| [4497](https://github.com/GBOGEB/ABACUS/security/code-scanning/4497) | Bandit | `B101` | `test_schema_validation.py` | 18 | note |
| [4496](https://github.com/GBOGEB/ABACUS/security/code-scanning/4496) | Bandit | `B101` | `test_schema_validation.py` | 14 | note |
| [4495](https://github.com/GBOGEB/ABACUS/security/code-scanning/4495) | Bandit | `B101` | `test_schema_validation.py` | 13 | note |
| [4494](https://github.com/GBOGEB/ABACUS/security/code-scanning/4494) | Bandit | `B101` | `test_schema_validation.py` | 12 | note |
| [4493](https://github.com/GBOGEB/ABACUS/security/code-scanning/4493) | Bandit | `B101` | `test_schema_validation.py` | 11 | note |
| [4492](https://github.com/GBOGEB/ABACUS/security/code-scanning/4492) | Bandit | `B101` | `test_runtime.py` | 126 | note |
| … | _1522 more — see alerts.yaml_ | | | | |

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

### ⚪ OTHER (514 alerts)

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
| … | _484 more — see alerts.yaml_ | | | | |

## Quick-Win Fix Order

| Priority | REX Group | Est. Alerts | Action |
|----------|-----------|------------:|--------|
| 1 | SEC_SUBPROCESS | 98 live / ~40 est. | Add `# noqa: S603` — all calls use list-form args |
| 2 | SEC_PATH_TRAVERSAL | 0 live / ~20 est. | `pathlib.Path(p).resolve(); assert is_relative_to(BASE)` |
| 3 | SEC_COMPILE_EXEC | 0 live / ~10 est. | Replace `compile+exec` with `ast.parse()` (syntax-only) |
| 4 | SEC_TEMPFILE | 32 live / ~15 est. | Remove `delete=False` from `NamedTemporaryFile` |
| 5 | SEC_ASSERT | 1552 live / ~10 est. | Add `# noqa: S101` in pytest files, raise in prod |
| 6 | QUAL_DEAD_CODE | 243 live / ~30 est. | `ruff check --fix --select F401,F841 DMAIC_V3/` |

_Dashboard last updated: 2026-08-19T16:46:06Z_
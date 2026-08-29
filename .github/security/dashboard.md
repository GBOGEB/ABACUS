# ABACUS Security Dashboard
> Auto-generated 2026-08-29T19:44:06Z · repo: `GBOGEB/ABACUS`  
> **3873 open alerts** across 3 tools

## Severity Overview

| Severity | Count |
|----------|------:|
| Error | 75 |
| Warning | 218 |
| Note | 3580 |

## Alerts by Tool

| Tool | Open Alerts |
|------|------------:|
| Bandit | 3315 |
| CodeQL | 493 |
| Semgrep | 65 |

## REX Group Summary
_Groups are defined in [security.toml](security.toml)_

| REX Group | Risk | Count | Fix Priority |
|-----------|------|------:|-------------|
| 🔴 SEC_SUBPROCESS | HIGH | 116 | Fix now |
| 🔴 SEC_HARDCODED_SECRET | HIGH | 21 | Fix now |
| 🟠 SEC_TEMPFILE | MEDIUM | 32 | Fix next sprint |
| 🟠 SEC_WEAK_HASH | MEDIUM | 10 | Fix next sprint |
| 🟡 SEC_ASSERT | LOW | 2911 | Suppress / defer |
| 🟡 QUAL_DEAD_CODE | LOW | 243 | Suppress / defer |
| ⚪ OTHER | INFO | 540 | Suppress / defer |

## Hottest Files (most alerts)

| File | Alert Count |
|------|------------:|
| `tests/test_dmaic_orchestration.py` | 82 |
| `tests/test_docker_integration.py` | 79 |
| `tests/test_bootstrap_eval.py` | 79 |
| `tests/test_user_library_rag.py` | 77 |
| `tests/test_phase_0_to_9_integration.py` | 77 |
| `tests/test_dow_keb_master_orchestrator.py` | 73 |
| `tests/test_action_tracker.py` | 72 |
| `tests/test_master_doc_manager.py` | 69 |
| `tests/test_advanced_security.py` | 61 |
| `DMAIC_V3/tests/test_log_monitor.py` | 60 |

## Alert Detail by REX Group

### 🔴 SEC_SUBPROCESS (116 alerts)

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
| [5250](https://github.com/GBOGEB/ABACUS/security/code-scanning/5250) | Bandit | `B603` | `test_docker_integration.py` | 415 | note |
| [5247](https://github.com/GBOGEB/ABACUS/security/code-scanning/5247) | Bandit | `B603` | `test_docker_integration.py` | 405 | note |
| [5244](https://github.com/GBOGEB/ABACUS/security/code-scanning/5244) | Bandit | `B603` | `test_docker_integration.py` | 391 | note |
| [5240](https://github.com/GBOGEB/ABACUS/security/code-scanning/5240) | Bandit | `B603` | `test_docker_integration.py` | 378 | note |
| [5237](https://github.com/GBOGEB/ABACUS/security/code-scanning/5237) | Bandit | `B603` | `test_docker_integration.py` | 366 | note |
| [5227](https://github.com/GBOGEB/ABACUS/security/code-scanning/5227) | Bandit | `B603` | `test_docker_integration.py` | 202 | note |
| [5224](https://github.com/GBOGEB/ABACUS/security/code-scanning/5224) | Bandit | `B603` | `test_docker_integration.py` | 192 | note |
| [5222](https://github.com/GBOGEB/ABACUS/security/code-scanning/5222) | Bandit | `B603` | `test_docker_integration.py` | 191 | note |
| [5220](https://github.com/GBOGEB/ABACUS/security/code-scanning/5220) | Bandit | `B603` | `test_docker_integration.py` | 181 | note |
| [5217](https://github.com/GBOGEB/ABACUS/security/code-scanning/5217) | Bandit | `B603` | `test_docker_integration.py` | 165 | note |
| [5214](https://github.com/GBOGEB/ABACUS/security/code-scanning/5214) | Bandit | `B603` | `test_docker_integration.py` | 154 | note |
| [5109](https://github.com/GBOGEB/ABACUS/security/code-scanning/5109) | Bandit | `B603` | `test_dmaic_orchestration.py` | 144 | note |
| [4965](https://github.com/GBOGEB/ABACUS/security/code-scanning/4965) | Bandit | `B603` | `test_container_registry.py` | 185 | note |
| [4963](https://github.com/GBOGEB/ABACUS/security/code-scanning/4963) | Bandit | `B603` | `test_container_registry.py` | 162 | note |
| [4961](https://github.com/GBOGEB/ABACUS/security/code-scanning/4961) | Bandit | `B603` | `test_container_registry.py` | 138 | note |
| [4959](https://github.com/GBOGEB/ABACUS/security/code-scanning/4959) | Bandit | `B603` | `test_container_registry.py` | 98 | note |
| [4957](https://github.com/GBOGEB/ABACUS/security/code-scanning/4957) | Bandit | `B603` | `test_container_registry.py` | 52 | note |
| [4676](https://github.com/GBOGEB/ABACUS/security/code-scanning/4676) | Bandit | `B603` | `bootstrap_bridge.py` | 183 | note |
| [4575](https://github.com/GBOGEB/ABACUS/security/code-scanning/4575) | Bandit | `B603` | `gen_kpi_dashboard.py` | 117 | note |
| [4573](https://github.com/GBOGEB/ABACUS/security/code-scanning/4573) | Bandit | `B603` | `gen_kpi_dashboard.py` | 112 | note |
| [4532](https://github.com/GBOGEB/ABACUS/security/code-scanning/4532) | Bandit | `B603` | `build_handover_package.py` | 98 | note |
| … | _86 more — see alerts.yaml_ | | | | |

### 🔴 SEC_HARDCODED_SECRET (21 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [5938](https://github.com/GBOGEB/ABACUS/security/code-scanning/5938) | Bandit | `B105` | `test_self_improvement.py` | 431 | note |
| [5771](https://github.com/GBOGEB/ABACUS/security/code-scanning/5771) | Bandit | `B105` | `test_phase_0_to_9_integration.py` | 27 | note |
| [5602](https://github.com/GBOGEB/ABACUS/security/code-scanning/5602) | Bandit | `B105` | `test_legacy_integration.py` | 114 | note |
| [5600](https://github.com/GBOGEB/ABACUS/security/code-scanning/5600) | Bandit | `B105` | `test_legacy_integration.py` | 113 | note |
| [5598](https://github.com/GBOGEB/ABACUS/security/code-scanning/5598) | Bandit | `B105` | `test_legacy_integration.py` | 101 | note |
| [5449](https://github.com/GBOGEB/ABACUS/security/code-scanning/5449) | Bandit | `B105` | `test_github_roundtrip_full.py` | 308 | note |
| [5448](https://github.com/GBOGEB/ABACUS/security/code-scanning/5448) | Bandit | `B105` | `test_github_roundtrip_full.py` | 308 | note |
| [5397](https://github.com/GBOGEB/ABACUS/security/code-scanning/5397) | Bandit | `B105` | `test_github_integration.py` | 16 | note |
| [5110](https://github.com/GBOGEB/ABACUS/security/code-scanning/5110) | Bandit | `B105` | `test_dmaic_orchestration.py` | 251 | note |
| [5107](https://github.com/GBOGEB/ABACUS/security/code-scanning/5107) | Bandit | `B105` | `test_dmaic_orchestration.py` | 104 | note |
| [4787](https://github.com/GBOGEB/ABACUS/security/code-scanning/4787) | Bandit | `B105` | `test_advanced_security.py` | 122 | note |
| [4786](https://github.com/GBOGEB/ABACUS/security/code-scanning/4786) | Bandit | `B105` | `test_advanced_security.py` | 112 | note |
| [4784](https://github.com/GBOGEB/ABACUS/security/code-scanning/4784) | Bandit | `B105` | `test_advanced_security.py` | 70 | note |
| [4677](https://github.com/GBOGEB/ABACUS/security/code-scanning/4677) | Bandit | `B105` | `bootstrap_bridge.py` | 388 | note |
| [4297](https://github.com/GBOGEB/ABACUS/security/code-scanning/4297) | Bandit | `B105` | `classify_artifacts.py` | 128 | note |
| [4292](https://github.com/GBOGEB/ABACUS/security/code-scanning/4292) | Bandit | `B105` | `analyze_repo.py` | 258 | note |
| [4221](https://github.com/GBOGEB/ABACUS/security/code-scanning/4221) | Bandit | `B105` | `collect_metrics.py` | 99 | note |
| [3911](https://github.com/GBOGEB/ABACUS/security/code-scanning/3911) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 374 | note |
| [3910](https://github.com/GBOGEB/ABACUS/security/code-scanning/3910) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 313 | note |
| [3909](https://github.com/GBOGEB/ABACUS/security/code-scanning/3909) | Bandit | `B105` | `abacus_v21_security_hardening.py` | 159 | note |
| [2747](https://github.com/GBOGEB/ABACUS/security/code-scanning/2747) | Bandit | `B105` | `log_monitor.py` | 26 | note |

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

### 🟡 SEC_ASSERT (2911 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [6086](https://github.com/GBOGEB/ABACUS/security/code-scanning/6086) | Bandit | `B101` | `test_yaml_validation.py` | 428 | note |
| [6085](https://github.com/GBOGEB/ABACUS/security/code-scanning/6085) | Bandit | `B101` | `test_yaml_validation.py` | 414 | note |
| [6084](https://github.com/GBOGEB/ABACUS/security/code-scanning/6084) | Bandit | `B101` | `test_yaml_validation.py` | 411 | note |
| [6083](https://github.com/GBOGEB/ABACUS/security/code-scanning/6083) | Bandit | `B101` | `test_yaml_validation.py` | 398 | note |
| [6082](https://github.com/GBOGEB/ABACUS/security/code-scanning/6082) | Bandit | `B101` | `test_yaml_validation.py` | 376 | note |
| [6081](https://github.com/GBOGEB/ABACUS/security/code-scanning/6081) | Bandit | `B101` | `test_yaml_validation.py` | 367 | note |
| [6080](https://github.com/GBOGEB/ABACUS/security/code-scanning/6080) | Bandit | `B101` | `test_yaml_validation.py` | 358 | note |
| [6079](https://github.com/GBOGEB/ABACUS/security/code-scanning/6079) | Bandit | `B101` | `test_yaml_validation.py` | 341 | note |
| [6078](https://github.com/GBOGEB/ABACUS/security/code-scanning/6078) | Bandit | `B101` | `test_yaml_validation.py` | 320 | note |
| [6077](https://github.com/GBOGEB/ABACUS/security/code-scanning/6077) | Bandit | `B101` | `test_yaml_validation.py` | 296 | note |
| [6076](https://github.com/GBOGEB/ABACUS/security/code-scanning/6076) | Bandit | `B101` | `test_yaml_validation.py` | 272 | note |
| [6075](https://github.com/GBOGEB/ABACUS/security/code-scanning/6075) | Bandit | `B101` | `test_yaml_validation.py` | 255 | note |
| [6074](https://github.com/GBOGEB/ABACUS/security/code-scanning/6074) | Bandit | `B101` | `test_yaml_validation.py` | 254 | note |
| [6073](https://github.com/GBOGEB/ABACUS/security/code-scanning/6073) | Bandit | `B101` | `test_yaml_validation.py` | 242 | note |
| [6072](https://github.com/GBOGEB/ABACUS/security/code-scanning/6072) | Bandit | `B101` | `test_yaml_validation.py` | 241 | note |
| [6071](https://github.com/GBOGEB/ABACUS/security/code-scanning/6071) | Bandit | `B101` | `test_yaml_validation.py` | 228 | note |
| [6070](https://github.com/GBOGEB/ABACUS/security/code-scanning/6070) | Bandit | `B101` | `test_yaml_validation.py` | 215 | note |
| [6069](https://github.com/GBOGEB/ABACUS/security/code-scanning/6069) | Bandit | `B101` | `test_yaml_validation.py` | 193 | note |
| [6068](https://github.com/GBOGEB/ABACUS/security/code-scanning/6068) | Bandit | `B101` | `test_yaml_validation.py` | 182 | note |
| [6067](https://github.com/GBOGEB/ABACUS/security/code-scanning/6067) | Bandit | `B101` | `test_yaml_validation.py` | 176 | note |
| [6066](https://github.com/GBOGEB/ABACUS/security/code-scanning/6066) | Bandit | `B101` | `test_yaml_validation.py` | 167 | note |
| [6065](https://github.com/GBOGEB/ABACUS/security/code-scanning/6065) | Bandit | `B101` | `test_yaml_validation.py` | 149 | note |
| [6064](https://github.com/GBOGEB/ABACUS/security/code-scanning/6064) | Bandit | `B101` | `test_yaml_validation.py` | 138 | note |
| [6063](https://github.com/GBOGEB/ABACUS/security/code-scanning/6063) | Bandit | `B101` | `test_yaml_validation.py` | 123 | note |
| [6062](https://github.com/GBOGEB/ABACUS/security/code-scanning/6062) | Bandit | `B101` | `test_yaml_validation.py` | 122 | note |
| [6061](https://github.com/GBOGEB/ABACUS/security/code-scanning/6061) | Bandit | `B101` | `test_yaml_validation.py` | 121 | note |
| [6060](https://github.com/GBOGEB/ABACUS/security/code-scanning/6060) | Bandit | `B101` | `test_yaml_validation.py` | 114 | note |
| [6059](https://github.com/GBOGEB/ABACUS/security/code-scanning/6059) | Bandit | `B101` | `test_yaml_validation.py` | 113 | note |
| [6058](https://github.com/GBOGEB/ABACUS/security/code-scanning/6058) | Bandit | `B101` | `test_yaml_validation.py` | 106 | note |
| [6057](https://github.com/GBOGEB/ABACUS/security/code-scanning/6057) | Bandit | `B101` | `test_yaml_validation.py` | 99 | note |
| … | _2881 more — see alerts.yaml_ | | | | |

### 🟡 QUAL_DEAD_CODE (243 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [4668](https://github.com/GBOGEB/ABACUS/security/code-scanning/4668) | CodeQL | `py/unused-import` | `test_yaml_validation.py` | 11 | note |
| [4667](https://github.com/GBOGEB/ABACUS/security/code-scanning/4667) | CodeQL | `py/unused-import` | `test_yaml_validation.py` | 10 | note |
| [4666](https://github.com/GBOGEB/ABACUS/security/code-scanning/4666) | CodeQL | `py/unused-import` | `test_week3_integration.py` | 11 | note |
| [4665](https://github.com/GBOGEB/ABACUS/security/code-scanning/4665) | CodeQL | `py/unused-import` | `test_user_library_rag.py` | 14 | note |
| [4664](https://github.com/GBOGEB/ABACUS/security/code-scanning/4664) | CodeQL | `py/unused-import` | `test_user_library_rag.py` | 12 | note |
| [4663](https://github.com/GBOGEB/ABACUS/security/code-scanning/4663) | CodeQL | `py/unused-import` | `test_self_improvement.py` | 17 | note |
| [4662](https://github.com/GBOGEB/ABACUS/security/code-scanning/4662) | CodeQL | `py/unused-import` | `test_self_improvement.py` | 13 | note |
| [4661](https://github.com/GBOGEB/ABACUS/security/code-scanning/4661) | CodeQL | `py/unused-import` | `test_refactoring_engine_protocols.py` | 21 | note |
| [4660](https://github.com/GBOGEB/ABACUS/security/code-scanning/4660) | CodeQL | `py/unused-import` | `test_refactoring_engine_protocols.py` | 16 | note |
| [4659](https://github.com/GBOGEB/ABACUS/security/code-scanning/4659) | CodeQL | `py/unused-import` | `test_reader_engine.py` | 24 | note |
| [4658](https://github.com/GBOGEB/ABACUS/security/code-scanning/4658) | CodeQL | `py/unused-import` | `test_reader_engine.py` | 19 | note |
| [4657](https://github.com/GBOGEB/ABACUS/security/code-scanning/4657) | CodeQL | `py/unused-import` | `test_phase_0_to_9_integration.py` | 12 | note |
| [4656](https://github.com/GBOGEB/ABACUS/security/code-scanning/4656) | CodeQL | `py/unused-import` | `test_phase_0_to_9_integration.py` | 11 | note |
| [4655](https://github.com/GBOGEB/ABACUS/security/code-scanning/4655) | CodeQL | `py/unused-import` | `test_parallel_execution.py` | 16 | note |
| [4654](https://github.com/GBOGEB/ABACUS/security/code-scanning/4654) | CodeQL | `py/unused-import` | `test_master_doc_manager.py` | 15 | note |
| [4653](https://github.com/GBOGEB/ABACUS/security/code-scanning/4653) | CodeQL | `py/unused-import` | `test_master_doc_manager.py` | 14 | note |
| [4652](https://github.com/GBOGEB/ABACUS/security/code-scanning/4652) | CodeQL | `py/unused-import` | `test_master_doc_manager.py` | 12 | note |
| [4651](https://github.com/GBOGEB/ABACUS/security/code-scanning/4651) | CodeQL | `py/unused-import` | `test_legacy_integration.py` | 10 | note |
| [4650](https://github.com/GBOGEB/ABACUS/security/code-scanning/4650) | CodeQL | `py/unused-import` | `test_legacy_integration.py` | 9 | note |
| [4649](https://github.com/GBOGEB/ABACUS/security/code-scanning/4649) | CodeQL | `py/unused-import` | `test_legacy_integration.py` | 8 | note |
| [4648](https://github.com/GBOGEB/ABACUS/security/code-scanning/4648) | CodeQL | `py/unused-import` | `test_keb_bridge.py` | 15 | note |
| [4647](https://github.com/GBOGEB/ABACUS/security/code-scanning/4647) | CodeQL | `py/unused-import` | `test_keb_bridge.py` | 13 | note |
| [4646](https://github.com/GBOGEB/ABACUS/security/code-scanning/4646) | CodeQL | `py/unused-import` | `test_integration_patch.py` | 10 | note |
| [4645](https://github.com/GBOGEB/ABACUS/security/code-scanning/4645) | CodeQL | `py/unused-import` | `test_integration_patch.py` | 9 | note |
| [4644](https://github.com/GBOGEB/ABACUS/security/code-scanning/4644) | CodeQL | `py/unused-import` | `test_integration_bootstrap_bridges.py` | 32 | note |
| [4643](https://github.com/GBOGEB/ABACUS/security/code-scanning/4643) | CodeQL | `py/unused-import` | `test_historical_sessions.py` | 15 | note |
| [4642](https://github.com/GBOGEB/ABACUS/security/code-scanning/4642) | CodeQL | `py/unused-import` | `test_historical_sessions.py` | 14 | note |
| [4641](https://github.com/GBOGEB/ABACUS/security/code-scanning/4641) | CodeQL | `py/unused-import` | `test_historical_sessions.py` | 13 | note |
| [4640](https://github.com/GBOGEB/ABACUS/security/code-scanning/4640) | CodeQL | `py/unused-import` | `test_github_roundtrip_full.py` | 12 | note |
| [4639](https://github.com/GBOGEB/ABACUS/security/code-scanning/4639) | CodeQL | `py/unused-import` | `test_github_integration.py` | 10 | note |
| … | _213 more — see alerts.yaml_ | | | | |

### ⚪ OTHER (540 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [4669](https://github.com/GBOGEB/ABACUS/security/code-scanning/4669) | CodeQL | `py/syntax-error` | `test_rtm_core.py` | 6 | error |
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
| … | _510 more — see alerts.yaml_ | | | | |

## Quick-Win Fix Order

| Priority | REX Group | Est. Alerts | Action |
|----------|-----------|------------:|--------|
| 1 | SEC_SUBPROCESS | 116 live / ~40 est. | Add `# noqa: S603` — all calls use list-form args |
| 2 | SEC_PATH_TRAVERSAL | 0 live / ~20 est. | `pathlib.Path(p).resolve(); assert is_relative_to(BASE)` |
| 3 | SEC_COMPILE_EXEC | 0 live / ~10 est. | Replace `compile+exec` with `ast.parse()` (syntax-only) |
| 4 | SEC_TEMPFILE | 32 live / ~15 est. | Remove `delete=False` from `NamedTemporaryFile` |
| 5 | SEC_ASSERT | 2911 live / ~10 est. | Add `# noqa: S101` in pytest files, raise in prod |
| 6 | QUAL_DEAD_CODE | 243 live / ~30 est. | `ruff check --fix --select F401,F841 DMAIC_V3/` |

_Dashboard last updated: 2026-08-29T19:44:06Z_
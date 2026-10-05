# ABACUS Security Dashboard
> Auto-generated 2026-10-05T08:15:46Z · repo: `GBOGEB/ABACUS`  
> **4922 open alerts** across 5 tools

## Severity Overview

| Severity | Count |
|----------|------:|
| Error | 139 |
| Warning | 1227 |
| Note | 3556 |

## Alerts by Tool

| Tool | Open Alerts |
|------|------------:|
| Bandit | 3318 |
| Semgrep OSS | 1016 |
| CodeQL | 406 |
| Trivy | 178 |
| Semgrep | 4 |

## REX Group Summary
_Groups are defined in [security.toml](security.toml)_

| REX Group | Risk | Count | Fix Priority |
|-----------|------|------:|-------------|
| 🔴 SEC_SUBPROCESS | HIGH | 118 | Fix now |
| 🔴 SEC_HARDCODED_SECRET | HIGH | 21 | Fix now |
| 🟠 SEC_TEMPFILE | MEDIUM | 32 | Fix next sprint |
| 🟠 SEC_WEAK_HASH | MEDIUM | 14 | Fix next sprint |
| 🟡 SEC_ASSERT | LOW | 2911 | Suppress / defer |
| 🟡 QUAL_DEAD_CODE | LOW | 194 | Suppress / defer |
| ⚪ OTHER | INFO | 1632 | Suppress / defer |

## Hottest Files (most alerts)

| File | Alert Count |
|------|------------:|
| `library/dmaic-pipeline` | 168 |
| `tests/test_dmaic_orchestration.py` | 80 |
| `tests/test_bootstrap_eval.py` | 79 |
| `tests/test_docker_integration.py` | 78 |
| `tests/test_phase_0_to_9_integration.py` | 77 |
| `tests/test_user_library_rag.py` | 77 |
| `tests/test_dow_keb_master_orchestrator.py` | 73 |
| `tests/test_action_tracker.py` | 72 |
| `tests/test_master_doc_manager.py` | 69 |
| `tests/test_advanced_security.py` | 61 |

## Alert Detail by REX Group

### 🔴 SEC_SUBPROCESS (118 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [7533](https://github.com/GBOGEB/ABACUS/security/code-scanning/7533) | Semgrep OSS | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `diagnostic_kpi_probe.py` | 16 | error |
| [7531](https://github.com/GBOGEB/ABACUS/security/code-scanning/7531) | Semgrep OSS | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `t0_deep_diagnostics.py` | 13 | error |
| [4316](https://github.com/GBOGEB/ABACUS/security/code-scanning/4316) | Bandit | `B602` | `cold_start_doctor.py` | 19 | error |
| [4307](https://github.com/GBOGEB/ABACUS/security/code-scanning/4307) | Bandit | `B602` | `run_streamlined_deployment.py` | 27 | error |
| [4305](https://github.com/GBOGEB/ABACUS/security/code-scanning/4305) | Bandit | `B602` | `run_comprehensive_deployment.py` | 46 | error |
| [4303](https://github.com/GBOGEB/ABACUS/security/code-scanning/4303) | Bandit | `B602` | `run_cicd_roundtrip_test.py` | 46 | error |
| [3950](https://github.com/GBOGEB/ABACUS/security/code-scanning/3950) | Bandit | `B602` | `deploy_full_integration.py` | 63 | error |
| [2476](https://github.com/GBOGEB/ABACUS/security/code-scanning/2476) | Semgrep OSS | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_streamlined_deployment.py` | 27 | error |
| [2475](https://github.com/GBOGEB/ABACUS/security/code-scanning/2475) | Semgrep OSS | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_comprehensive_deployment.py` | 48 | error |
| [2474](https://github.com/GBOGEB/ABACUS/security/code-scanning/2474) | Semgrep OSS | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `run_cicd_roundtrip_test.py` | 48 | error |
| [2473](https://github.com/GBOGEB/ABACUS/security/code-scanning/2473) | Semgrep OSS | `python.lang.security.audit.subprocess-shell-true.subprocess-shell-true` | `deploy_full_integration.py` | 65 | error |
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
| … | _88 more — see alerts.yaml_ | | | | |

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

### 🟠 SEC_WEAK_HASH (14 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [4296](https://github.com/GBOGEB/ABACUS/security/code-scanning/4296) | Bandit | `B324` | `classify_artifacts.py` | 68 | error |
| [3951](https://github.com/GBOGEB/ABACUS/security/code-scanning/3951) | Bandit | `B324` | `fast_metrics_collector.py` | 72 | error |
| [2759](https://github.com/GBOGEB/ABACUS/security/code-scanning/2759) | Bandit | `B324` | `phase8_todo_management.py` | 40 | error |
| [2757](https://github.com/GBOGEB/ABACUS/security/code-scanning/2757) | Bandit | `B324` | `phase7_action_tracking.py` | 37 | error |
| [2704](https://github.com/GBOGEB/ABACUS/security/code-scanning/2704) | Bandit | `B324` | `canonical_refactoring.py` | 159 | error |
| [775](https://github.com/GBOGEB/ABACUS/security/code-scanning/775) | Bandit | `B324` | `phase8_todo_management.py` | 40 | error |
| [773](https://github.com/GBOGEB/ABACUS/security/code-scanning/773) | Bandit | `B324` | `phase7_action_tracking.py` | 37 | error |
| [716](https://github.com/GBOGEB/ABACUS/security/code-scanning/716) | Bandit | `B324` | `canonical_refactoring.py` | 159 | error |
| [7534](https://github.com/GBOGEB/ABACUS/security/code-scanning/7534) | Semgrep OSS | `python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1` | `w285_recompute_federation_depth.py` | 16 | warning |
| [2489](https://github.com/GBOGEB/ABACUS/security/code-scanning/2489) | Semgrep OSS | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `fast_metrics_collector.py` | 73 | warning |
| [2488](https://github.com/GBOGEB/ABACUS/security/code-scanning/2488) | Semgrep OSS | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `phase8_todo_management.py` | 40 | warning |
| [2487](https://github.com/GBOGEB/ABACUS/security/code-scanning/2487) | Semgrep OSS | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `phase7_action_tracking.py` | 37 | warning |
| [2486](https://github.com/GBOGEB/ABACUS/security/code-scanning/2486) | Semgrep OSS | `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` | `canonical_refactoring.py` | 159 | warning |
| [2472](https://github.com/GBOGEB/ABACUS/security/code-scanning/2472) | Semgrep OSS | `python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1` | `classify_artifacts.py` | 68 | warning |

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

### 🟡 QUAL_DEAD_CODE (194 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [7839](https://github.com/GBOGEB/ABACUS/security/code-scanning/7839) | CodeQL | `py/unused-import` | `test_phase1_define_coverage.py` | 1 | note |
| [7837](https://github.com/GBOGEB/ABACUS/security/code-scanning/7837) | CodeQL | `py/unused-import` | `github_azure_deployment_helper.py` | 19 | note |
| [7836](https://github.com/GBOGEB/ABACUS/security/code-scanning/7836) | CodeQL | `py/unused-import` | `demo_integrated_system.py` | 24 | note |
| [7835](https://github.com/GBOGEB/ABACUS/security/code-scanning/7835) | CodeQL | `py/unused-import` | `abacus_v21_security_hardening.py` | 18 | note |
| [7834](https://github.com/GBOGEB/ABACUS/security/code-scanning/7834) | CodeQL | `py/unused-import` | `abacus_v21_postdeployment_validation.py` | 21 | note |
| [7833](https://github.com/GBOGEB/ABACUS/security/code-scanning/7833) | CodeQL | `py/unused-import` | `abacus_v21_production_deployment.py` | 21 | note |
| [7832](https://github.com/GBOGEB/ABACUS/security/code-scanning/7832) | CodeQL | `py/unused-import` | `abacus_v21_postcd_summary.py` | 13 | note |
| [7831](https://github.com/GBOGEB/ABACUS/security/code-scanning/7831) | CodeQL | `py/unused-import` | `abacus_v21_knowledge_preservation.py` | 21 | note |
| [7830](https://github.com/GBOGEB/ABACUS/security/code-scanning/7830) | CodeQL | `py/unused-import` | `abacus_v21_environment_preparation.py` | 18 | note |
| [7829](https://github.com/GBOGEB/ABACUS/security/code-scanning/7829) | CodeQL | `py/unused-import` | `abacus_v21_dry_run_tests.py` | 21 | note |
| [7828](https://github.com/GBOGEB/ABACUS/security/code-scanning/7828) | CodeQL | `py/unused-import` | `abacus_v21_bridge_validation_tests.py` | 24 | note |
| [7827](https://github.com/GBOGEB/ABACUS/security/code-scanning/7827) | CodeQL | `py/unused-import` | `abacus_v21_backup_recovery.py` | 18 | note |
| [7811](https://github.com/GBOGEB/ABACUS/security/code-scanning/7811) | CodeQL | `py/unused-import` | `master_reconciliation.py` | 26 | note |
| [7810](https://github.com/GBOGEB/ABACUS/security/code-scanning/7810) | CodeQL | `py/unused-import` | `master_reconciliation.py` | 23 | note |
| [7809](https://github.com/GBOGEB/ABACUS/security/code-scanning/7809) | CodeQL | `py/unused-import` | `verify_alignment.py` | 10 | note |
| [7808](https://github.com/GBOGEB/ABACUS/security/code-scanning/7808) | CodeQL | `py/unused-import` | `local_deployment_runner.py` | 9 | note |
| [7807](https://github.com/GBOGEB/ABACUS/security/code-scanning/7807) | CodeQL | `py/unused-import` | `github_deployment_orchestrator.py` | 9 | note |
| [7806](https://github.com/GBOGEB/ABACUS/security/code-scanning/7806) | CodeQL | `py/unused-import` | `validate_cicd_deployment.py` | 16 | note |
| [7805](https://github.com/GBOGEB/ABACUS/security/code-scanning/7805) | CodeQL | `py/unused-import` | `validate_cicd_deployment.py` | 12 | note |
| [7590](https://github.com/GBOGEB/ABACUS/security/code-scanning/7590) | CodeQL | `py/unused-import` | `test_integration_patch.py` | 10 | note |
| [7589](https://github.com/GBOGEB/ABACUS/security/code-scanning/7589) | CodeQL | `py/unused-import` | `test_integration_patch.py` | 9 | note |
| [7588](https://github.com/GBOGEB/ABACUS/security/code-scanning/7588) | CodeQL | `py/unused-import` | `test_github_roundtrip_full.py` | 12 | note |
| [7587](https://github.com/GBOGEB/ABACUS/security/code-scanning/7587) | CodeQL | `py/unused-import` | `fetch_workflow_errors.py` | 12 | note |
| [7582](https://github.com/GBOGEB/ABACUS/security/code-scanning/7582) | CodeQL | `py/unused-import` | `test_phase_0_to_9_integration.py` | 12 | note |
| [7581](https://github.com/GBOGEB/ABACUS/security/code-scanning/7581) | CodeQL | `py/unused-import` | `run_direct_improvements.py` | 10 | note |
| [7580](https://github.com/GBOGEB/ABACUS/security/code-scanning/7580) | CodeQL | `py/unused-import` | `run_direct_improvements.py` | 9 | note |
| [7536](https://github.com/GBOGEB/ABACUS/security/code-scanning/7536) | CodeQL | `py/unused-import` | `t0_deep_diagnostics.py` | 3 | note |
| [7535](https://github.com/GBOGEB/ABACUS/security/code-scanning/7535) | CodeQL | `py/unused-import` | `deterministic_census_authority_and_contract_check.py` | 2 | note |
| [7501](https://github.com/GBOGEB/ABACUS/security/code-scanning/7501) | CodeQL | `py/unused-import` | `phase0_runner.py` | 8 | note |
| [7465](https://github.com/GBOGEB/ABACUS/security/code-scanning/7465) | CodeQL | `py/unused-import` | `ci_monitor_local.py` | 17 | note |
| … | _164 more — see alerts.yaml_ | | | | |

### ⚪ OTHER (1632 alerts)

| # | Tool | Rule | File | Line | Severity |
|---|------|------|------|-----:|---------:|
| [7773](https://github.com/GBOGEB/ABACUS/security/code-scanning/7773) | Semgrep OSS | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `dow-sprint6-cicd.yml` | 425 | error |
| [7772](https://github.com/GBOGEB/ABACUS/security/code-scanning/7772) | Semgrep OSS | `yaml.github-actions.security.run-shell-injection.run-shell-injection` | `dow-sprint6-cicd.yml` | 122 | error |
| [7770](https://github.com/GBOGEB/ABACUS/security/code-scanning/7770) | Trivy | `CVE-2026-24049` | `METADATA` | 1 | error |
| [7768](https://github.com/GBOGEB/ABACUS/security/code-scanning/7768) | Trivy | `CVE-2026-97689` | `Python` | 1 | error |
| [7767](https://github.com/GBOGEB/ABACUS/security/code-scanning/7767) | Trivy | `CVE-2026-97687` | `Python` | 1 | error |
| [7765](https://github.com/GBOGEB/ABACUS/security/code-scanning/7765) | Trivy | `CVE-2025-47273` | `Python` | 1 | error |
| [7762](https://github.com/GBOGEB/ABACUS/security/code-scanning/7762) | Trivy | `GHSA-6v7p-g79w-8964` | `Python` | 1 | error |
| [7761](https://github.com/GBOGEB/ABACUS/security/code-scanning/7761) | Trivy | `CVE-2026-23949` | `METADATA` | 1 | error |
| [7756](https://github.com/GBOGEB/ABACUS/security/code-scanning/7756) | Trivy | `CVE-2026-78410` | `dmaic-pipeline` | 1 | error |
| [7755](https://github.com/GBOGEB/ABACUS/security/code-scanning/7755) | Trivy | `CVE-2026-78409` | `dmaic-pipeline` | 1 | error |
| [7754](https://github.com/GBOGEB/ABACUS/security/code-scanning/7754) | Trivy | `CVE-2026-78408` | `dmaic-pipeline` | 1 | error |
| [7753](https://github.com/GBOGEB/ABACUS/security/code-scanning/7753) | Trivy | `CVE-2026-76642` | `dmaic-pipeline` | 1 | error |
| [7742](https://github.com/GBOGEB/ABACUS/security/code-scanning/7742) | Trivy | `CVE-2026-9538` | `dmaic-pipeline` | 1 | error |
| [7737](https://github.com/GBOGEB/ABACUS/security/code-scanning/7737) | Trivy | `CVE-2025-69720` | `dmaic-pipeline` | 1 | error |
| [7735](https://github.com/GBOGEB/ABACUS/security/code-scanning/7735) | Trivy | `CVE-2025-69720` | `dmaic-pipeline` | 1 | error |
| [7732](https://github.com/GBOGEB/ABACUS/security/code-scanning/7732) | Trivy | `CVE-2026-78410` | `dmaic-pipeline` | 1 | error |
| [7731](https://github.com/GBOGEB/ABACUS/security/code-scanning/7731) | Trivy | `CVE-2026-78409` | `dmaic-pipeline` | 1 | error |
| [7730](https://github.com/GBOGEB/ABACUS/security/code-scanning/7730) | Trivy | `CVE-2026-78408` | `dmaic-pipeline` | 1 | error |
| [7729](https://github.com/GBOGEB/ABACUS/security/code-scanning/7729) | Trivy | `CVE-2026-76642` | `dmaic-pipeline` | 1 | error |
| [7723](https://github.com/GBOGEB/ABACUS/security/code-scanning/7723) | Trivy | `CVE-2026-78410` | `dmaic-pipeline` | 1 | error |
| [7722](https://github.com/GBOGEB/ABACUS/security/code-scanning/7722) | Trivy | `CVE-2026-78409` | `dmaic-pipeline` | 1 | error |
| [7721](https://github.com/GBOGEB/ABACUS/security/code-scanning/7721) | Trivy | `CVE-2026-78408` | `dmaic-pipeline` | 1 | error |
| [7720](https://github.com/GBOGEB/ABACUS/security/code-scanning/7720) | Trivy | `CVE-2026-76642` | `dmaic-pipeline` | 1 | error |
| [7717](https://github.com/GBOGEB/ABACUS/security/code-scanning/7717) | Trivy | `CVE-2026-78410` | `dmaic-pipeline` | 1 | error |
| [7716](https://github.com/GBOGEB/ABACUS/security/code-scanning/7716) | Trivy | `CVE-2026-78409` | `dmaic-pipeline` | 1 | error |
| [7715](https://github.com/GBOGEB/ABACUS/security/code-scanning/7715) | Trivy | `CVE-2026-78408` | `dmaic-pipeline` | 1 | error |
| [7714](https://github.com/GBOGEB/ABACUS/security/code-scanning/7714) | Trivy | `CVE-2026-76642` | `dmaic-pipeline` | 1 | error |
| [7707](https://github.com/GBOGEB/ABACUS/security/code-scanning/7707) | Trivy | `CVE-2026-16742` | `dmaic-pipeline` | 1 | error |
| [7705](https://github.com/GBOGEB/ABACUS/security/code-scanning/7705) | Trivy | `CVE-2025-69720` | `dmaic-pipeline` | 1 | error |
| [7698](https://github.com/GBOGEB/ABACUS/security/code-scanning/7698) | Trivy | `CVE-2026-16742` | `dmaic-pipeline` | 1 | error |
| … | _1602 more — see alerts.yaml_ | | | | |

## Quick-Win Fix Order

| Priority | REX Group | Est. Alerts | Action |
|----------|-----------|------------:|--------|
| 1 | SEC_SUBPROCESS | 118 live / ~40 est. | Add `# noqa: S603` — all calls use list-form args |
| 2 | SEC_PATH_TRAVERSAL | 0 live / ~20 est. | `pathlib.Path(p).resolve(); assert is_relative_to(BASE)` |
| 3 | SEC_COMPILE_EXEC | 0 live / ~10 est. | Replace `compile+exec` with `ast.parse()` (syntax-only) |
| 4 | SEC_TEMPFILE | 32 live / ~15 est. | Remove `delete=False` from `NamedTemporaryFile` |
| 5 | SEC_ASSERT | 2911 live / ~10 est. | Add `# noqa: S101` in pytest files, raise in prod |
| 6 | QUAL_DEAD_CODE | 194 live / ~30 est. | `ruff check --fix --select F401,F841 DMAIC_V3/` |

_Dashboard last updated: 2026-10-05T08:15:46Z_
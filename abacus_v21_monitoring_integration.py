#!/usr/bin/env python3
"""
ABACUS v2.1 - Stage 2.3: Monitoring Integration
POST-CD Phase - Production Monitoring and Observability

This script sets up comprehensive monitoring and observability for ABACUS v2.1.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class MonitoringIntegration:
    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.output_dir = Path("ABACUS_V21_MONITORING")
        self.output_dir.mkdir(exist_ok=True)
        
        self.results = {
            "stage": "2.3",
            "name": "Monitoring Integration",
            "timestamp": self.timestamp,
            "monitoring_systems": [],
            "dashboards": [],
            "alerts": [],
            "recommendations": []
        }
    
    def create_logging_config(self) -> Dict[str, Any]:
        """Create comprehensive logging configuration"""
        config = {
            "name": "Logging Configuration",
            "status": "CREATED",
            "details": {}
        }
        
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
                },
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "json",
                    "filename": "logs/abacus_v21.log",
                    "maxBytes": 10485760,
                    "backupCount": 10
                },
                "error_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "json",
                    "filename": "logs/abacus_v21_errors.log",
                    "maxBytes": 10485760,
                    "backupCount": 10
                }
            },
            "loggers": {
                "abacus": {
                    "level": "DEBUG",
                    "handlers": ["console", "file", "error_file"],
                    "propagate": False
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["console", "file"]
            }
        }
        
        config_path = self.output_dir / "logging_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(logging_config, f, indent=2)
        
        config["details"]["config_file"] = str(config_path)
        config["details"]["handlers"] = list(logging_config["handlers"].keys())
        config["message"] = f"Logging configuration created with {len(logging_config['handlers'])} handlers"
        
        return config
    
    def create_metrics_config(self) -> Dict[str, Any]:
        """Create metrics collection configuration"""
        config = {
            "name": "Metrics Configuration",
            "status": "CREATED",
            "details": {}
        }
        
        metrics_config = {
            "version": "2.1.0",
            "timestamp": self.timestamp,
            "collection": {
                "interval": 60,
                "retention": "30d"
            },
            "metrics": {
                "system": {
                    "cpu_usage": {
                        "enabled": True,
                        "unit": "percent",
                        "threshold": 80
                    },
                    "memory_usage": {
                        "enabled": True,
                        "unit": "megabytes",
                        "threshold": 512
                    },
                    "disk_usage": {
                        "enabled": True,
                        "unit": "percent",
                        "threshold": 90
                    }
                },
                "application": {
                    "execution_time": {
                        "enabled": True,
                        "unit": "seconds",
                        "threshold": 300
                    },
                    "error_count": {
                        "enabled": True,
                        "unit": "count",
                        "threshold": 10
                    },
                    "success_rate": {
                        "enabled": True,
                        "unit": "percent",
                        "threshold": 95
                    },
                    "artifact_count": {
                        "enabled": True,
                        "unit": "count"
                    }
                },
                "integration": {
                    "dmaic_dow_bridge": {
                        "enabled": True,
                        "metric": "coverage_percent"
                    },
                    "recursive_temporal_bridge": {
                        "enabled": True,
                        "metric": "artifact_count"
                    },
                    "state_config_bridge": {
                        "enabled": True,
                        "metric": "validity_percent"
                    },
                    "output_artifact_bridge": {
                        "enabled": True,
                        "metric": "artifact_count"
                    }
                }
            },
            "exporters": {
                "prometheus": {
                    "enabled": True,
                    "port": 9090,
                    "path": "/metrics"
                },
                "json": {
                    "enabled": True,
                    "output": "logs/metrics.json"
                }
            }
        }
        
        config_path = self.output_dir / "metrics_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(metrics_config, f, indent=2)
        
        config["details"]["config_file"] = str(config_path)
        config["details"]["metric_categories"] = list(metrics_config["metrics"].keys())
        config["message"] = "Metrics configuration created"
        
        return config
    
    def create_alert_rules(self) -> Dict[str, Any]:
        """Create alerting rules"""
        config = {
            "name": "Alert Rules",
            "status": "CREATED",
            "details": {}
        }
        
        alert_rules = {
            "version": "2.1.0",
            "timestamp": self.timestamp,
            "rules": [
                {
                    "name": "High CPU Usage",
                    "condition": "cpu_usage > 80",
                    "severity": "WARNING",
                    "duration": "5m",
                    "action": "notify",
                    "channels": ["email", "log"]
                },
                {
                    "name": "High Memory Usage",
                    "condition": "memory_usage > 512",
                    "severity": "WARNING",
                    "duration": "5m",
                    "action": "notify",
                    "channels": ["email", "log"]
                },
                {
                    "name": "High Error Rate",
                    "condition": "error_count > 10",
                    "severity": "ERROR",
                    "duration": "1m",
                    "action": "notify",
                    "channels": ["email", "log", "slack"]
                },
                {
                    "name": "Low Success Rate",
                    "condition": "success_rate < 95",
                    "severity": "WARNING",
                    "duration": "10m",
                    "action": "notify",
                    "channels": ["email", "log"]
                },
                {
                    "name": "Execution Timeout",
                    "condition": "execution_time > 300",
                    "severity": "ERROR",
                    "duration": "1m",
                    "action": "notify",
                    "channels": ["email", "log", "slack"]
                },
                {
                    "name": "Bridge Health Check Failed",
                    "condition": "bridge_health == false",
                    "severity": "CRITICAL",
                    "duration": "1m",
                    "action": "notify",
                    "channels": ["email", "log", "slack", "pagerduty"]
                }
            ],
            "notification_channels": {
                "email": {
                    "enabled": True,
                    "recipients": ["team@example.com"]
                },
                "log": {
                    "enabled": True,
                    "file": "logs/alerts.log"
                },
                "slack": {
                    "enabled": False,
                    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
                },
                "pagerduty": {
                    "enabled": False,
                    "integration_key": "YOUR_PAGERDUTY_KEY"
                }
            }
        }
        
        config_path = self.output_dir / "alert_rules.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(alert_rules, f, indent=2)
        
        config["details"]["config_file"] = str(config_path)
        config["details"]["rule_count"] = len(alert_rules["rules"])
        config["message"] = f"Alert rules created with {len(alert_rules['rules'])} rules"
        
        return config
    
    def create_dashboard_config(self) -> Dict[str, Any]:
        """Create monitoring dashboard configuration"""
        config = {
            "name": "Dashboard Configuration",
            "status": "CREATED",
            "details": {}
        }
        
        dashboard = {
            "version": "2.1.0",
            "timestamp": self.timestamp,
            "dashboards": [
                {
                    "name": "System Overview",
                    "panels": [
                        {"title": "CPU Usage", "type": "graph", "metric": "cpu_usage"},
                        {"title": "Memory Usage", "type": "graph", "metric": "memory_usage"},
                        {"title": "Disk Usage", "type": "gauge", "metric": "disk_usage"},
                        {"title": "System Health", "type": "status", "metric": "health_status"}
                    ]
                },
                {
                    "name": "Application Performance",
                    "panels": [
                        {"title": "Execution Time", "type": "graph", "metric": "execution_time"},
                        {"title": "Success Rate", "type": "gauge", "metric": "success_rate"},
                        {"title": "Error Count", "type": "counter", "metric": "error_count"},
                        {"title": "Throughput", "type": "graph", "metric": "throughput"}
                    ]
                },
                {
                    "name": "Integration Bridges",
                    "panels": [
                        {"title": "DMAIC-DOW Bridge", "type": "status", "metric": "dmaic_dow_coverage"},
                        {"title": "Recursive-Temporal Bridge", "type": "counter", "metric": "recursive_temporal_artifacts"},
                        {"title": "State-Config Bridge", "type": "gauge", "metric": "state_config_validity"},
                        {"title": "Output-Artifact Bridge", "type": "counter", "metric": "output_artifacts"}
                    ]
                },
                {
                    "name": "Test Results",
                    "panels": [
                        {"title": "Test Pass Rate", "type": "gauge", "metric": "test_pass_rate"},
                        {"title": "Test Execution Time", "type": "graph", "metric": "test_execution_time"},
                        {"title": "Failed Tests", "type": "counter", "metric": "failed_tests"},
                        {"title": "Test Coverage", "type": "gauge", "metric": "test_coverage"}
                    ]
                }
            ]
        }
        
        config_path = self.output_dir / "dashboard_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, indent=2)
        
        config["details"]["config_file"] = str(config_path)
        config["details"]["dashboard_count"] = len(dashboard["dashboards"])
        config["message"] = f"Dashboard configuration created with {len(dashboard['dashboards'])} dashboards"
        
        return config
    
    def create_health_check_script(self) -> Dict[str, Any]:
        """Create health check script"""
        config = {
            "name": "Health Check Script",
            "status": "CREATED",
            "details": {}
        }
        
        health_check = """#!/usr/bin/env python3
\"\"\"
ABACUS v2.1 Health Check Script
Performs comprehensive system health checks
\"\"\"

import sys
import json
from datetime import datetime
from pathlib import Path

def check_core_modules():
    \"\"\"Check if core modules are importable\"\"\"
    modules = [
        "execute_full_pipeline_sprint_dow",
        "dmaic_v3_orchestrator",
        "recursive_knowledge_engine",
        "temporal_session_analyzer"
    ]
    
    results = []
    for module in modules:
        try:
            __import__(module)
            results.append({"module": module, "status": "OK"})
        except ImportError as e:
            results.append({"module": module, "status": "FAIL", "error": str(e)})
    
    return results

def check_directories():
    \"\"\"Check if required directories exist\"\"\"
    dirs = [
        "DMAIC_V3_OUTPUT",
        "ABACUS_V21_KNOWLEDGE_BASE",
        "logs",
        "config"
    ]
    
    results = []
    for dir_name in dirs:
        exists = Path(dir_name).exists()
        results.append({"directory": dir_name, "status": "OK" if exists else "MISSING"})
    
    return results

def check_configuration():
    \"\"\"Check if configuration files are valid\"\"\"
    configs = [
        "DOW_IMPLEMENTATION_TRACKER.json",
        "ABACUS_V21_PROGRESS_TRACKER.yaml"
    ]
    
    results = []
    for config_file in configs:
        path = Path(config_file)
        if path.exists():
            results.append({"config": config_file, "status": "OK"})
        else:
            results.append({"config": config_file, "status": "MISSING"})
    
    return results

def main():
    print("ABACUS v2.1 Health Check")
    print("=" * 50)
    
    health = {
        "timestamp": datetime.now().isoformat(),
        "status": "HEALTHY",
        "checks": {
            "modules": check_core_modules(),
            "directories": check_directories(),
            "configuration": check_configuration()
        }
    }
    
    # Determine overall health
    all_checks = (
        health["checks"]["modules"] +
        health["checks"]["directories"] +
        health["checks"]["configuration"]
    )
    
    failed = [c for c in all_checks if c.get("status") not in ["OK", "HEALTHY"]]
    if failed:
        health["status"] = "UNHEALTHY"
        health["failed_checks"] = len(failed)
    
    print(json.dumps(health, indent=2))
    
    return 0 if health["status"] == "HEALTHY" else 1

if __name__ == "__main__":
    sys.exit(main())
"""
        
        script_path = self.output_dir / "health_check.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(health_check)
        
        config["details"]["script_file"] = str(script_path)
        config["message"] = "Health check script created"
        
        return config
    
    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate monitoring recommendations"""
        recommendations = [
            {
                "priority": "HIGH",
                "category": "OBSERVABILITY",
                "title": "Implement Distributed Tracing",
                "description": "Add distributed tracing for end-to-end visibility",
                "action": "Integrate OpenTelemetry or Jaeger for request tracing"
            },
            {
                "priority": "HIGH",
                "category": "ALERTING",
                "title": "Configure Alert Escalation",
                "description": "Set up alert escalation policies",
                "action": "Define escalation paths for different severity levels"
            },
            {
                "priority": "HIGH",
                "category": "MONITORING",
                "title": "Deploy Monitoring Stack",
                "description": "Deploy Prometheus, Grafana, or similar monitoring stack",
                "action": "Set up monitoring infrastructure and dashboards"
            },
            {
                "priority": "MEDIUM",
                "category": "LOGGING",
                "title": "Centralize Log Aggregation",
                "description": "Implement centralized log aggregation",
                "action": "Deploy ELK stack or similar log aggregation solution"
            },
            {
                "priority": "MEDIUM",
                "category": "PERFORMANCE",
                "title": "Add Performance Profiling",
                "description": "Implement performance profiling and APM",
                "action": "Integrate application performance monitoring tools"
            }
        ]
        
        return recommendations
    
    def run_integration(self):
        """Run complete monitoring integration"""
        print("=" * 80)
        print("ABACUS v2.1 - Stage 2.3: Monitoring Integration")
        print("=" * 80)
        print()
        
        print("Creating monitoring configurations...")
        self.results["monitoring_systems"].append(self.create_logging_config())
        self.results["monitoring_systems"].append(self.create_metrics_config())
        
        print("\nCreating alert rules...")
        self.results["alerts"].append(self.create_alert_rules())
        
        print("\nCreating dashboards...")
        self.results["dashboards"].append(self.create_dashboard_config())
        
        print("\nCreating health check script...")
        self.results["monitoring_systems"].append(self.create_health_check_script())
        
        print("\nGenerating recommendations...")
        self.results["recommendations"] = self.generate_recommendations()
        
        self.save_results()
        self.generate_report()
        
        print("\n" + "=" * 80)
        print("Monitoring Integration Complete")
        print("=" * 80)
    
    def save_results(self):
        """Save results to JSON"""
        results_path = self.output_dir / "monitoring_integration_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {results_path}")
    
    def generate_report(self):
        """Generate markdown report"""
        report_path = self.output_dir / "MONITORING_INTEGRATION_REPORT.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# ABACUS v2.1 - Monitoring Integration Report\n\n")
            f.write(f"**Stage**: 2.3 - Monitoring Integration\n")
            f.write(f"**Timestamp**: {self.timestamp}\n")
            f.write(f"**Phase**: POST-CD\n\n")
            f.write("---\n\n")
            
            f.write("## Monitoring Systems\n\n")
            for system in self.results["monitoring_systems"]:
                f.write(f"### [CREATED] {system['name']}\n\n")
                f.write(f"**Status**: {system['status']}\n")
                f.write(f"**Message**: {system['message']}\n\n")
            
            f.write("## Alert Configuration\n\n")
            for alert in self.results["alerts"]:
                f.write(f"### [CREATED] {alert['name']}\n\n")
                f.write(f"**Status**: {alert['status']}\n")
                f.write(f"**Message**: {alert['message']}\n\n")
            
            f.write("## Dashboards\n\n")
            for dashboard in self.results["dashboards"]:
                f.write(f"### [CREATED] {dashboard['name']}\n\n")
                f.write(f"**Status**: {dashboard['status']}\n")
                f.write(f"**Message**: {dashboard['message']}\n\n")
            
            f.write("## Recommendations\n\n")
            for rec in self.results["recommendations"]:
                priority_icon = "HIGH" if rec["priority"] == "HIGH" else "MEDIUM"
                f.write(f"### [{priority_icon}] {rec['title']}\n\n")
                f.write(f"**Category**: {rec['category']}\n")
                f.write(f"**Description**: {rec['description']}\n")
                f.write(f"**Action**: {rec['action']}\n\n")
            
            f.write("---\n\n")
            f.write("## Next Steps\n\n")
            f.write("1. Deploy monitoring infrastructure (Prometheus, Grafana)\n")
            f.write("2. Configure alert notification channels\n")
            f.write("3. Set up log aggregation system\n")
            f.write("4. Test health check script\n")
            f.write("5. Proceed to Stage 2.4: Production Deployment\n\n")
            f.write("---\n\n")
            f.write(f"*Report generated on {self.timestamp}*\n")
        
        print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    monitoring = MonitoringIntegration()
    monitoring.run_integration()

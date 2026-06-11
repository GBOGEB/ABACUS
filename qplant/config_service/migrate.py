"""QPLANT Configuration Migration Tool.

Migrates configuration from direct file reads (config_loader.py) to
the centralised config service. Also supports schema upgrades.

Usage:
    python -m config_service.migrate --check       # Dry-run check
    python -m config_service.migrate --execute     # Run migration
    python -m config_service.migrate --rollback    # Rollback last migration
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml


class ConfigMigration:
    """Handles configuration schema migrations and system integration."""

    def __init__(self, config_path: str = "data/config.yaml"):
        self.config_path = Path(config_path).resolve()
        self.backup_dir = self.config_path.parent / "backups"
        self.migration_log: List[Dict[str, Any]] = []

    def check(self) -> Dict[str, Any]:
        """Dry-run migration check. Returns report of what would change."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config_path": str(self.config_path),
            "config_exists": self.config_path.exists(),
            "checks": [],
            "migrations_needed": [],
        }

        if not self.config_path.exists():
            report["checks"].append({"check": "file_exists", "status": "FAIL", "detail": "Config file not found"})
            return report

        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check version format
        version = config.get("version", "")
        parts = version.split(".")
        version_ok = len(parts) == 3 and all(p.isdigit() for p in parts)
        report["checks"].append({
            "check": "version_format",
            "status": "PASS" if version_ok else "FAIL",
            "detail": f"Version: {version}",
        })

        # Check required sections
        required_sections = [
            "system", "flow_parameters", "pressure_parameters",
            "compressor_specifications", "financial", "compliance",
        ]
        for section in required_sections:
            present = section in config
            report["checks"].append({
                "check": f"section_{section}",
                "status": "PASS" if present else "FAIL",
                "detail": f"{'Present' if present else 'Missing'}",
            })
            if not present:
                report["migrations_needed"].append(f"Add missing section: {section}")

        # Check compressor count alignment
        hp_count = config.get("compressor_specifications", {}).get("hp_compressors", {}).get("count", 0)
        if hp_count != 3:
            report["migrations_needed"].append(f"Fix compressor count: {hp_count} → 3")

        # Check for environment overlay files
        for env in ["dev", "staging", "prod", "dr"]:
            overlay = self.config_path.parent / f"config.{env}.yaml"
            report["checks"].append({
                "check": f"env_overlay_{env}",
                "status": "PASS" if overlay.exists() else "INFO",
                "detail": f"{'Exists' if overlay.exists() else 'Not created (optional)'}",
            })

        report["overall"] = "PASS" if not report["migrations_needed"] else "NEEDS_MIGRATION"
        return report

    def execute(self, target_version: str = "4.2.0") -> Dict[str, Any]:
        """Execute migration to target version."""
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_version": target_version,
            "steps": [],
            "success": True,
        }

        # 1. Backup current config
        backup_path = self._backup()
        result["steps"].append({"step": "backup", "status": "OK", "path": str(backup_path)})

        # 2. Load config
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # 3. Update version
        old_version = config.get("version", "unknown")
        config["version"] = target_version
        config["last_updated"] = datetime.now(timezone.utc).isoformat()
        result["steps"].append({
            "step": "version_update",
            "status": "OK",
            "detail": f"{old_version} → {target_version}",
        })

        # 4. Create environment overlays if missing
        for env in ["dev", "staging", "prod", "dr"]:
            overlay_path = self.config_path.parent / f"config.{env}.yaml"
            if not overlay_path.exists():
                overlay = self._generate_env_overlay(env)
                with open(overlay_path, "w") as f:
                    yaml.dump(overlay, f, default_flow_style=False)
                result["steps"].append({
                    "step": f"create_overlay_{env}",
                    "status": "OK",
                    "path": str(overlay_path),
                })

        # 5. Save migrated config
        with open(self.config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        result["steps"].append({"step": "save_config", "status": "OK"})

        return result

    def rollback(self) -> Dict[str, Any]:
        """Rollback to the latest backup."""
        if not self.backup_dir.exists():
            return {"status": "FAIL", "detail": "No backups found"}

        backups = sorted(self.backup_dir.glob("config_*.yaml"), reverse=True)
        if not backups:
            return {"status": "FAIL", "detail": "No backup files found"}

        latest = backups[0]
        shutil.copy2(latest, self.config_path)
        return {
            "status": "OK",
            "restored_from": str(latest),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _backup(self) -> Path:
        """Create timestamped backup of current config."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"config_{timestamp}.yaml"
        shutil.copy2(self.config_path, backup_path)
        return backup_path

    def _generate_env_overlay(self, env: str) -> Dict[str, Any]:
        """Generate environment-specific overlay."""
        overlays = {
            "dev": {
                "description": "Development environment overlay",
                "financial": {
                    "electricity_cost_eur_kwh": 0.10,
                },
            },
            "staging": {
                "description": "Staging environment overlay",
            },
            "prod": {
                "description": "Production environment overlay",
            },
            "dr": {
                "description": "Disaster recovery environment overlay",
            },
        }
        return overlays.get(env, {"description": f"{env} overlay"})


def main():
    parser = argparse.ArgumentParser(description="QPLANT Config Migration Tool")
    parser.add_argument("--check", action="store_true", help="Dry-run check")
    parser.add_argument("--execute", action="store_true", help="Execute migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback last migration")
    parser.add_argument("--config", default="data/config.yaml", help="Config file path")
    parser.add_argument("--version", default="4.2.0", help="Target version")
    args = parser.parse_args()

    migration = ConfigMigration(args.config)

    if args.check:
        result = migration.check()
        print(json.dumps(result, indent=2))
    elif args.execute:
        result = migration.execute(target_version=args.version)
        print(json.dumps(result, indent=2))
    elif args.rollback:
        result = migration.rollback()
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

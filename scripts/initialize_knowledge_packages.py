#!/usr/bin/env python3
"""
DMAIC V3.3 - Knowledge Package Initialization Script
Version: 3.3.0
Updated: 2025-11-12

This script initializes knowledge packages for AI agents, providing them with:
- DMAIC process documentation
- Code structure and patterns
- Metrics and KPIs
- Best practices and guidelines
"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

VERSION = "3.3.0"

def _write_if_changed(path: Path, content: str) -> str:
    """Write content only if changed; returns 'created' | 'updated' | 'skipped'"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return "skipped"
        path.write_text(content, encoding="utf-8")
        return "updated"
    path.write_text(content, encoding="utf-8")
    return "created"

class KnowledgePackageInitializer:
    """Initialize and manage knowledge packages for AI agents"""
    
    def __init__(self, workspace_root: Path = Path(".")):
        self.workspace_root = workspace_root
        self.knowledge_dir = workspace_root / "knowledge_packages"
        self.knowledge_dir.mkdir(exist_ok=True)
        
    def create_dmaic_knowledge_package(self) -> Dict[str, Any]:
        """Create comprehensive DMAIC knowledge package"""
        
        package = {
            "package_name": "DMAIC_V3_Core_Knowledge",
            "version": VERSION,
            "created": datetime.now().isoformat(),
            "description": "Core DMAIC V3.3 process knowledge for AI agents",
            
            "process_overview": {
                "methodology": "DMAIC (Define, Measure, Analyze, Improve, Control)",
                "version": "3.3.0",
                "phases": [
                    {
                        "id": "phase0",
                        "name": "Setup & Initialization",
                        "purpose": "Validate environment and dependencies",
                        "outputs": ["system_checks", "environment_validation"]
                    },
                    {
                        "id": "phase1",
                        "name": "Define",
                        "purpose": "Scan and categorize workspace files",
                        "outputs": ["file_inventory", "categorization", "relationships"]
                    },
                    {
                        "id": "phase2",
                        "name": "Measure",
                        "purpose": "Analyze code metrics and quality",
                        "outputs": ["code_metrics", "complexity_analysis", "dependencies"]
                    },
                    {
                        "id": "phase3",
                        "name": "Analyze",
                        "purpose": "Identify patterns and issues",
                        "outputs": ["quality_assessment", "pattern_detection", "issue_identification"]
                    },
                    {
                        "id": "phase4",
                        "name": "Improve",
                        "purpose": "Generate improvement recommendations",
                        "outputs": ["refactoring_suggestions", "optimization_opportunities"]
                    },
                    {
                        "id": "phase5",
                        "name": "Control",
                        "purpose": "Establish quality gates and monitoring",
                        "outputs": ["quality_gates", "monitoring_rules", "control_mechanisms"]
                    },
                    {
                        "id": "phase6",
                        "name": "Knowledge",
                        "purpose": "Capture and distribute learnings",
                        "outputs": ["knowledge_packages", "best_practices", "lessons_learned"]
                    }
                ]
            },
            
            "key_concepts": {
                "idempotency": "All operations can be safely re-executed without side effects",
                "ranking": "Artifacts are classified and prioritized based on importance",
                "metrics": "Comprehensive KPIs track process health and progress",
                "change_detection": "Only modified components are re-processed"
            },
            
            "file_structure": {
                "DMAIC_V3/": "Core engine and phase implementations",
                "DMAIC_V3_OUTPUT/": "Execution results and metrics",
                ".github/workflows/": "CI/CD pipeline definitions",
                "artifacts/": "Generated artifacts and reports",
                "knowledge_packages/": "AI agent knowledge bases"
            },
            
            "quality_gates": {
                "complexity_threshold": 500,
                "file_size_limit": 500,
                "import_limit": 20,
                "test_coverage_minimum": 80
            },
            
            "best_practices": [
                "Always run Phase 0 before other phases",
                "Review metrics after each execution",
                "Update rankings regularly",
                "Maintain idempotency in all operations",
                "Document all changes and decisions"
            ],
            
            "common_commands": {
                "dry_run": "python -m DMAIC_V3.dmaic_v3_engine --mode dry-run",
                "full_cycle": "python -m DMAIC_V3.dmaic_v3_engine --mode full --iterations 1",
                "single_phase": "python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase1_define",
                "check_metrics": "python scripts/check_convergence.py"
            },
            
            "troubleshooting": {
                "version_error": "Check python_min_version in DMAIC_V3/config.py",
                "import_error": "Verify all dependencies in requirements.txt",
                "phase_failure": "Review logs in DMAIC_V3_OUTPUT/iteration_*/phase*/",
                "metrics_missing": "Ensure ENABLE_METRICS=true in environment"
            }
        }
        
        return package
    
    def create_agent_context(self) -> Dict[str, Any]:
        """Create agent-specific context and guidelines"""
        
        context = {
            "agent_role": "DMAIC Process Assistant",
            "version": VERSION,
            "created": datetime.now().isoformat(),
            
            "capabilities": [
                "Execute DMAIC phases",
                "Analyze code quality",
                "Generate metrics and reports",
                "Provide improvement recommendations",
                "Update artifact rankings"
            ],
            
            "guidelines": {
                "code_analysis": [
                    "Focus on maintainability and readability",
                    "Identify complexity hotspots",
                    "Suggest refactoring opportunities",
                    "Respect existing patterns and conventions"
                ],
                "metrics_interpretation": [
                    "Compare against quality gates",
                    "Identify trends over time",
                    "Highlight critical issues",
                    "Provide actionable insights"
                ],
                "recommendations": [
                    "Be specific and actionable",
                    "Prioritize by impact and effort",
                    "Consider team capacity",
                    "Align with project goals"
                ]
            },
            
            "response_templates": {
                "phase_completion": "Phase {phase} completed successfully. {summary}",
                "issue_found": "Issue detected in {location}: {description}. Recommendation: {action}",
                "metric_alert": "Metric {metric} exceeded threshold: {value} > {threshold}",
                "improvement_suggestion": "Improvement opportunity: {description}. Expected benefit: {benefit}"
            },
            
            "knowledge_sources": [
                "DMAIC_TEMPORAL_MAPPING_COMPLETE.md",
                "DMAIC_V3_3_IMPLEMENTATION_SUMMARY.md",
                "DMAIC_V3_EXECUTION_SUMMARY.md",
                "CONVERGENCE_QUICK_REFERENCE.md"
            ]
        }
        
        return context
    
    def initialize_all_packages(self):
        """Initialize all knowledge packages (idempotent writes)"""
        print(f"🚀 Initializing Knowledge Packages v{VERSION}")
        print(f"📁 Output directory: {self.knowledge_dir}")
        
        dmaic_package = self.create_dmaic_knowledge_package()
        agent_context = self.create_agent_context()

        # JSON
        dmaic_json_path = self.knowledge_dir / "dmaic_core_knowledge.json"
        agent_json_path = self.knowledge_dir / "agent_context.json"
        res = _write_if_changed(dmaic_json_path, json.dumps(dmaic_package, indent=2))
        print(f"✅ {res.title()}: {dmaic_json_path}")
        res = _write_if_changed(agent_json_path, json.dumps(agent_context, indent=2))
        print(f"✅ {res.title()}: {agent_json_path}")

        # YAML
        dmaic_yaml_path = self.knowledge_dir / "dmaic_core_knowledge.yaml"
        agent_yaml_path = self.knowledge_dir / "agent_context.yaml"
        res = _write_if_changed(dmaic_yaml_path, yaml.safe_dump(dmaic_package, default_flow_style=False, sort_keys=False))
        print(f"✅ {res.title()}: {dmaic_yaml_path}")
        res = _write_if_changed(agent_yaml_path, yaml.safe_dump(agent_context, default_flow_style=False, sort_keys=False))
        print(f"✅ {res.title()}: {agent_yaml_path}")

        # README
        readme_path = self.knowledge_dir / "README.md"
        readme_content = f"""# DMAIC V3.3 Knowledge Packages

**Version:** {VERSION}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

This directory contains knowledge packages for AI agents working with the DMAIC V3.3 system.

## Files

- `dmaic_core_knowledge.json/yaml` - Core DMAIC process knowledge
- `agent_context.json/yaml` - Agent-specific context and guidelines
- `README.md` - This file

## Usage

AI agents should load these knowledge packages to understand:
- DMAIC process phases and workflows
- Code structure and patterns
- Quality gates and metrics
- Best practices and guidelines
- Common commands and troubleshooting

## Updates

Knowledge packages are automatically updated when:
- DMAIC version changes
- New phases are added
- Quality gates are modified
- Best practices evolve

## Integration

To integrate with your AI agent:

```python
import json

# Load DMAIC knowledge
with open('knowledge_packages/dmaic_core_knowledge.json') as f:
    dmaic_knowledge = json.load(f)

# Load agent context
with open('knowledge_packages/agent_context.json') as f:
    agent_context = json.load(f)
```

## Support

For questions or updates, refer to:
- DMAIC_V3_EXECUTION_SUMMARY.md
- CONVERGENCE_QUICK_REFERENCE.md
"""
        res = _write_if_changed(readme_path, readme_content)
        print(f"✅ {res.title()}: {readme_path}")
        
        print(f"\n✅ Knowledge package initialization complete!")
        print(f"📦 {len(list(self.knowledge_dir.glob('*')))} files present")

if __name__ == "__main__":
    initializer = KnowledgePackageInitializer()
    initializer.initialize_all_packages()

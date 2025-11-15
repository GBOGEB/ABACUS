# ARTIFACT RANKING & CLASSIFICATION SYSTEM V3.0
**Version**: 3.0.0  
**Date**: 2025-01-12  
**Purpose**: Self-ranking, comparative analysis, and hierarchical classification system for all project artifacts

---

## EXECUTIVE SUMMARY

This system provides:
1. **Self-ranking algorithm** - Each artifact scores itself (0-100) across multiple dimensions
2. **Comparative ranking** - Compare two artifacts (same type or cross-type)
3. **Type/Group/Function classification** - Hierarchical organization
4. **Maturity assessment** - 0=planning, 1=foundation, 2=development, 3=production
5. **Integration status tracking** - standalone | partially_integrated | fully_integrated

**Use Cases**:
- Identify high-priority artifacts for refactoring
- Detect duplicate/redundant files
- Track quality improvements over DMAIC iterations
- Generate artifact dependency graphs
- Prioritize testing and documentation efforts

---

## PART I: CLASSIFICATION TAXONOMY

### A. Type Classification

```yaml
artifact_types:
  code:
    python:
      extensions: [".py"]
      priority: "high"
      quality_checks: ["linting", "complexity", "type_hints", "test_coverage"]
      maturity_gates:
        1: "basic_syntax_valid"
        2: "tested_and_documented"
        3: "production_grade_with_ci"
      
    javascript:
      extensions: [".js", ".ts"]
      priority: "medium"
      quality_checks: ["eslint", "complexity"]
      
  documentation:
    markdown:
      extensions: [".md"]
      priority: "high"
      quality_checks: ["completeness", "links_valid", "version_tracked"]
      maturity_gates:
        1: "basic_structure"
        2: "cross_referenced"
        3: "canonical_with_ci"
    
    text:
      extensions: [".txt"]
      priority: "low"
      quality_checks: ["readability"]
  
  configuration:
    yaml:
      extensions: [".yaml", ".yml"]
      priority: "critical"
      quality_checks: ["schema_valid", "no_secrets", "consistent"]
      maturity_gates:
        1: "valid_yaml"
        2: "schema_compliant"
        3: "integrated_in_ci"
    
    json:
      extensions: [".json"]
      priority: "high"
      quality_checks: ["schema_valid", "no_secrets"]
  
  data:
    database:
      extensions: [".db", ".sqlite", ".sql"]
      priority: "critical"
      quality_checks: ["schema_integrity", "no_corruption"]
    
    reports:
      extensions: [".log", ".report"]
      priority: "low"
      quality_checks: ["temporal_relevance"]
  
  build:
    makefiles:
      extensions: ["Makefile", ".mk"]
      priority: "medium"
      quality_checks: ["syntax_valid"]
    
    dockerfiles:
      extensions: ["Dockerfile", ".dockerfile"]
      priority: "medium"
      quality_checks: ["best_practices", "security"]
```

### B. Group Classification

```yaml
artifact_groups:
  core_engine:
    description: "Orchestrator, KEB, GBOGEB, Temporal Scanner, Metrics Collector"
    priority: "critical"
    maturity_required: 3
    components:
      - "core/orchestrator/*"
      - "core/keb/*"
      - "core/gbogeb/*"
      - "core/temporal/*"
    quality_threshold: 90
    
  agents:
    description: "12-cluster analysis/documentation/recursive agents"
    priority: "critical"
    maturity_required: 2
    components:
      - "local_mcp/agents/*"
      - "agents/*"
    quality_threshold: 85
    
  dmaic_engine:
    description: "DMAIC V3 recursive engine and phases"
    priority: "critical"
    maturity_required: 2
    components:
      - "DMAIC_V3/*"
      - "src/dmaic/*"
    quality_threshold: 85
    
  tools:
    description: "Indexing, tracking, generation utilities"
    priority: "high"
    maturity_required: 2
    components:
      - "tools_v2.3/*"
      - "tools/*"
    quality_threshold: 80
    
  tests:
    description: "Unit, integration, smoke tests"
    priority: "high"
    maturity_required: 2
    components:
      - "tests/*"
      - "*_test.py"
      - "smoke_test_*.py"
    quality_threshold: 75
    
  documentation:
    description: "READMEs, handovers, guides, reports"
    priority: "medium"
    maturity_required: 1
    components:
      - "docs_versioned/*"
      - "*.md"
      - "HANDOVER*.md"
    quality_threshold: 70
    
  configuration:
    description: "YAML, JSON, ENV configs"
    priority: "critical"
    maturity_required: 2
    components:
      - "*.yaml"
      - "*.yml"
      - "config/*"
      - "HUMAN.yml"
    quality_threshold: 95
    
  cicd:
    description: "GitHub workflows, CI/CD pipelines"
    priority: "high"
    maturity_required: 2
    components:
      - ".github/workflows/*"
      - "scripts/*"
    quality_threshold: 85
    
  legacy:
    description: "V2.2 and earlier artifacts, deprecated code"
    priority: "low"
    maturity_required: 0
    components:
      - "docs_versioned/v2.2_archived/*"
      - "*_v2.2.py"
      - "*_v2.1.py"
    quality_threshold: 0
    archive_candidate: true
```

### C. Function Classification

```yaml
artifact_functions:
  execution:
    description: "Code that runs workflows (orchestrators, agents, tools)"
    priority: "critical"
    examples:
      - "orchestrator_v3.py"
      - "dmaic_v3_engine.py"
      - "analysis_cryo_dm_v2.3_OPTIMIZED.py"
    
  configuration:
    description: "YAML, JSON config files"
    priority: "critical"
    examples:
      - "HUMAN.yml"
      - "orchestrator_config.yaml"
      - "config/dmaic.yaml"
    
  validation:
    description: "Tests, smoke tests, validators"
    priority: "high"
    examples:
      - "smoke_test_runner.py"
      - "tests/test_*.py"
      - "comprehensive_dmaic_test.py"
    
  tracking:
    description: "Temporal tracking, metrics collection"
    priority: "high"
    examples:
      - "temporal_tracker.py"
      - "dmaic_v23_integration_tracker.py"
      - "execution_tracker.py"
    
  generation:
    description: "Code generation, report generation"
    priority: "medium"
    examples:
      - "code_index_generator_v2.3.py"
      - "handover_generator.py"
      - "create_chatready_code_v2.3_20251111.py"
    
  documentation:
    description: "Markdown, TXT explanatory files"
    priority: "medium"
    examples:
      - "README.md"
      - "HANDOVER*.md"
      - "COMPREHENSIVE_REFACTORING_*.md"
    
  reporting:
    description: "Logs, execution summaries, dashboards"
    priority: "low"
    examples:
      - "EXECUTION_SUMMARY.md"
      - "DMAIC_V2.1_TEST_EXECUTION_SUMMARY.md"
      - "*.log"
```

---

## PART II: SELF-RANKING ALGORITHM

### A. Quality Score Calculation (0-100)

```python
# artifact_ranking_engine.py

import os
import ast
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ArtifactRanking:
    """Data class for artifact ranking results"""
    path: str
    type: str
    group: str
    function: str
    maturity_level: int  # 0-3
    integration_status: str  # standalone|partial|full
    quality_score: float  # 0-100
    priority_rank: str  # critical|high|medium|low
    dependencies: List[str]
    dependent_artifacts: List[str]
    last_modified: str
    version: str
    canonical_location: str
    actions_required: List[str]
    metrics: Dict

class ArtifactRankingEngine:
    """Self-ranking engine for all project artifacts"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.rankings = {}
    
    def rank_artifact(self, artifact_path: str) -> ArtifactRanking:
        """Main entry point for artifact ranking"""
        
        path = Path(artifact_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")
        
        # Classify artifact
        artifact_type = self._classify_type(path)
        artifact_group = self._classify_group(path)
        artifact_function = self._classify_function(path)
        
        # Assess maturity
        maturity = self._assess_maturity(path, artifact_type)
        
        # Check integration status
        integration = self._check_integration(path)
        
        # Calculate quality score
        quality = self._calculate_quality(path, artifact_type, maturity)
        
        # Determine priority
        priority = self._determine_priority(artifact_group, artifact_function, maturity)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(path, artifact_type)
        dependents = self._find_dependents(path)
        
        # Get metadata
        last_modified = self._get_last_modified(path)
        version = self._extract_version(path, artifact_type)
        canonical = self._determine_canonical_location(path, artifact_group)
        
        # Determine actions
        actions = self._determine_actions(
            path, artifact_type, maturity, quality, integration, canonical
        )
        
        # Collect metrics
        metrics = self._collect_metrics(path, artifact_type)
        
        ranking = ArtifactRanking(
            path=str(path),
            type=artifact_type,
            group=artifact_group,
            function=artifact_function,
            maturity_level=maturity,
            integration_status=integration,
            quality_score=quality,
            priority_rank=priority,
            dependencies=dependencies,
            dependent_artifacts=dependents,
            last_modified=last_modified,
            version=version,
            canonical_location=canonical,
            actions_required=actions,
            metrics=metrics
        )
        
        self.rankings[str(path)] = ranking
        return ranking
    
    # ============ TYPE CLASSIFICATION ============
    
    def _classify_type(self, path: Path) -> str:
        """Classify artifact by file type"""
        
        suffix = path.suffix.lower()
        
        if suffix == ".py":
            return "code:python"
        elif suffix in [".js", ".ts"]:
            return "code:javascript"
        elif suffix == ".md":
            return "documentation:markdown"
        elif suffix == ".txt":
            return "documentation:text"
        elif suffix in [".yaml", ".yml"]:
            return "configuration:yaml"
        elif suffix == ".json":
            return "configuration:json"
        elif suffix in [".db", ".sqlite", ".sql"]:
            return "data:database"
        elif suffix in [".log", ".report"]:
            return "data:reports"
        elif path.name in ["Makefile", "Dockerfile"]:
            return "build:makefiles"
        else:
            return "unknown"
    
    # ============ GROUP CLASSIFICATION ============
    
    def _classify_group(self, path: Path) -> str:
        """Classify artifact by functional group"""
        
        path_str = str(path).replace("\\", "/")
        
        if any(x in path_str for x in ["core/orchestrator", "core/keb", "core/gbogeb", "core/temporal"]):
            return "core_engine"
        elif "agents/" in path_str or "local_mcp/agents/" in path_str:
            return "agents"
        elif "DMAIC_V3/" in path_str or "src/dmaic/" in path_str:
            return "dmaic_engine"
        elif "tools" in path_str:
            return "tools"
        elif "test" in path_str.lower() or "smoke" in path_str.lower():
            return "tests"
        elif ".github/workflows/" in path_str or "scripts/" in path_str:
            return "cicd"
        elif path.suffix in [".yaml", ".yml", ".json"] and "config" in path_str:
            return "configuration"
        elif path.suffix == ".md" or "docs" in path_str:
            return "documentation"
        elif "v2.2" in path_str or "archived" in path_str:
            return "legacy"
        else:
            return "uncategorized"
    
    # ============ FUNCTION CLASSIFICATION ============
    
    def _classify_function(self, path: Path) -> str:
        """Classify artifact by function"""
        
        path_str = str(path).lower()
        
        if "orchestrator" in path_str or "engine" in path_str or "agent" in path_str:
            return "execution"
        elif path.suffix in [".yaml", ".yml", ".json"] and "config" in path_str:
            return "configuration"
        elif "test" in path_str or "smoke" in path_str:
            return "validation"
        elif "tracker" in path_str or "metrics" in path_str:
            return "tracking"
        elif "generator" in path_str or "create_" in path_str:
            return "generation"
        elif path.suffix == ".md":
            return "documentation"
        elif ".log" in path_str or "summary" in path_str or "report" in path_str:
            return "reporting"
        else:
            return "utility"
    
    # ============ MATURITY ASSESSMENT ============
    
    def _assess_maturity(self, path: Path, artifact_type: str) -> int:
        """Assess artifact maturity (0-3)"""
        
        if artifact_type == "code:python":
            return self._assess_python_maturity(path)
        elif artifact_type in ["documentation:markdown", "documentation:text"]:
            return self._assess_documentation_maturity(path)
        elif artifact_type in ["configuration:yaml", "configuration:json"]:
            return self._assess_configuration_maturity(path)
        else:
            return 1  # Default maturity
    
    def _assess_python_maturity(self, path: Path) -> int:
        """Assess Python code maturity"""
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Check for basic validity
            if not tree:
                return 0
            
            # Check for docstrings, type hints, tests
            has_docstrings = any(
                ast.get_docstring(node) for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module))
            )
            
            has_type_hints = any(
                node.returns or any(arg.annotation for arg in node.args.args)
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            )
            
            # Check for tests
            test_file = path.parent / f"test_{path.name}"
            has_tests = test_file.exists()
            
            # Determine maturity
            if has_docstrings and has_type_hints and has_tests:
                return 3  # Production grade
            elif has_docstrings or has_type_hints:
                return 2  # Development grade
            else:
                return 1  # Foundation grade
                
        except Exception:
            return 0  # Planning/invalid
    
    def _assess_documentation_maturity(self, path: Path) -> int:
        """Assess documentation maturity"""
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check length
            if len(content) < 100:
                return 0
            
            # Check structure (headers, lists, etc.)
            has_structure = any(x in content for x in ["##", "###", "- ", "* ", "1. "])
            
            # Check for version tracking
            has_version = "version" in content.lower() or "v2" in content.lower() or "v3" in content.lower()
            
            # Check for cross-references
            has_references = ".md" in content or "see also" in content.lower()
            
            if has_structure and has_version and has_references:
                return 3
            elif has_structure and has_version:
                return 2
            elif has_structure:
                return 1
            else:
                return 0
                
        except Exception:
            return 0
    
    def _assess_configuration_maturity(self, path: Path) -> int:
        """Assess configuration file maturity"""
        
        try:
            if path.suffix in [".yaml", ".yml"]:
                import yaml
                with open(path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            elif path.suffix == ".json":
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                return 0
            
            # Valid if parseable
            if not data:
                return 0
            
            # Check for schema/version
            has_version = "version" in data or "Version" in data
            
            # Check if integrated in CI (look for references in workflows)
            ci_integrated = self._is_referenced_in_ci(path)
            
            if has_version and ci_integrated:
                return 3
            elif has_version:
                return 2
            else:
                return 1
                
        except Exception:
            return 0
    
    # ============ INTEGRATION STATUS ============
    
    def _check_integration(self, path: Path) -> str:
        """Check integration status"""
        
        # Check if file is imported/referenced by others
        references = self._find_references(path)
        
        if len(references) >= 5:
            return "fully_integrated"
        elif len(references) >= 1:
            return "partially_integrated"
        else:
            return "standalone"
    
    # ============ QUALITY SCORE ============
    
    def _calculate_quality(self, path: Path, artifact_type: str, maturity: int) -> float:
        """Calculate quality score (0-100)"""
        
        if artifact_type == "code:python":
            return self._calculate_python_quality(path, maturity)
        elif artifact_type in ["documentation:markdown", "documentation:text"]:
            return self._calculate_documentation_quality(path, maturity)
        elif artifact_type in ["configuration:yaml", "configuration:json"]:
            return self._calculate_configuration_quality(path, maturity)
        else:
            return maturity * 25.0  # Default: maturity-based score
    
    def _calculate_python_quality(self, path: Path, maturity: int) -> float:
        """Calculate Python code quality"""
        
        scores = []
        
        # Base maturity score (25%)
        scores.append(("maturity", maturity * 25.0, 0.25))
        
        # Complexity score (20%)
        complexity_score = self._check_complexity(path)
        scores.append(("complexity", complexity_score, 0.20))
        
        # Test coverage (25%)
        coverage_score = self._check_test_coverage(path)
        scores.append(("coverage", coverage_score, 0.25))
        
        # Documentation completeness (15%)
        doc_score = self._check_documentation_completeness(path)
        scores.append(("documentation", doc_score, 0.15))
        
        # Type hints coverage (10%)
        type_hints_score = self._check_type_hints(path)
        scores.append(("type_hints", type_hints_score, 0.10))
        
        # Linting compliance (5%)
        linting_score = self._check_linting(path)
        scores.append(("linting", linting_score, 0.05))
        
        # Calculate weighted sum
        total_score = sum(score * weight for _, score, weight in scores)
        
        return round(total_score, 2)
    
    def _check_complexity(self, path: Path) -> float:
        """Check cyclomatic complexity (inverse score)"""
        
        try:
            # Simple complexity check via radon or manual AST analysis
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Count decision points (if, for, while, except)
            complexity = sum(
                1 for node in ast.walk(tree)
                if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler))
            )
            
            # Inverse scale: lower complexity = higher score
            if complexity < 10:
                return 100.0
            elif complexity < 20:
                return 80.0
            elif complexity < 30:
                return 60.0
            elif complexity < 50:
                return 40.0
            else:
                return 20.0
                
        except Exception:
            return 50.0  # Default
    
    def _check_test_coverage(self, path: Path) -> float:
        """Check test coverage"""
        
        # Look for corresponding test file
        test_file = path.parent / f"test_{path.name}"
        
        if test_file.exists():
            # TODO: Actually run coverage tool
            return 85.0  # Placeholder
        else:
            return 0.0
    
    def _check_documentation_completeness(self, path: Path) -> float:
        """Check documentation completeness"""
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Count functions/classes with docstrings
            total = 0
            documented = 0
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    total += 1
                    if ast.get_docstring(node):
                        documented += 1
            
            if total == 0:
                return 100.0
            
            return (documented / total) * 100
            
        except Exception:
            return 50.0
    
    def _check_type_hints(self, path: Path) -> float:
        """Check type hints coverage"""
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Count functions with type hints
            total = 0
            typed = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    total += 1
                    if node.returns or any(arg.annotation for arg in node.args.args):
                        typed += 1
            
            if total == 0:
                return 100.0
            
            return (typed / total) * 100
            
        except Exception:
            return 50.0
    
    def _check_linting(self, path: Path) -> float:
        """Check linting compliance"""
        
        try:
            # Run pylint (if available)
            result = subprocess.run(
                ["pylint", str(path), "--score=yes"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse score from output
            for line in result.stdout.split('\n'):
                if "Your code has been rated at" in line:
                    score = float(line.split("rated at ")[1].split("/")[0])
                    return (score / 10) * 100
            
            return 70.0  # Default if can't parse
            
        except Exception:
            return 70.0  # Default if pylint not available
    
    def _calculate_documentation_quality(self, path: Path, maturity: int) -> float:
        """Calculate documentation quality"""
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            scores = []
            
            # Maturity (30%)
            scores.append(maturity * 25.0 * 0.30)
            
            # Length (20%)
            length_score = min(len(content) / 5000 * 100, 100)
            scores.append(length_score * 0.20)
            
            # Structure (20%)
            structure_score = (
                (content.count("##") + content.count("###")) / 10 * 100
            )
            structure_score = min(structure_score, 100)
            scores.append(structure_score * 0.20)
            
            # Links (15%)
            links_score = min(content.count(".md") * 10, 100)
            scores.append(links_score * 0.15)
            
            # Version tracking (15%)
            version_score = 100 if "version" in content.lower() else 0
            scores.append(version_score * 0.15)
            
            return round(sum(scores), 2)
            
        except Exception:
            return maturity * 25.0
    
    def _calculate_configuration_quality(self, path: Path, maturity: int) -> float:
        """Calculate configuration quality"""
        
        # Configuration files: primarily maturity-based
        return maturity * 30.0  # Max 90 for maturity 3
    
    # ============ HELPER METHODS ============
    
    def _determine_priority(self, group: str, function: str, maturity: int) -> str:
        """Determine priority rank"""
        
        if group in ["core_engine", "configuration"] and function == "execution":
            return "critical"
        elif group in ["agents", "dmaic_engine"] and maturity >= 2:
            return "critical"
        elif group in ["tools", "tests", "cicd"]:
            return "high"
        elif group == "documentation":
            return "medium"
        else:
            return "low"
    
    def _extract_dependencies(self, path: Path, artifact_type: str) -> List[str]:
        """Extract dependencies"""
        
        if artifact_type == "code:python":
            return self._extract_python_imports(path)
        else:
            return []
    
    def _extract_python_imports(self, path: Path) -> List[str]:
        """Extract Python imports"""
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            return imports
            
        except Exception:
            return []
    
    def _find_dependents(self, path: Path) -> List[str]:
        """Find artifacts that depend on this one"""
        
        # This would require scanning the entire codebase
        # Placeholder for now
        return []
    
    def _find_references(self, path: Path) -> List[str]:
        """Find references to this artifact"""
        
        # This would require scanning the entire codebase
        # Placeholder for now
        return []
    
    def _is_referenced_in_ci(self, path: Path) -> bool:
        """Check if artifact is referenced in CI workflows"""
        
        workflows_path = self.root_path / ".github" / "workflows"
        
        if not workflows_path.exists():
            return False
        
        path_str = str(path).replace("\\", "/")
        
        for workflow_file in workflows_path.glob("*.yml"):
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if path.name in content or path_str in content:
                    return True
                    
            except Exception:
                continue
        
        return False
    
    def _get_last_modified(self, path: Path) -> str:
        """Get last modified timestamp"""
        
        try:
            import datetime
            timestamp = os.path.getmtime(path)
            return datetime.datetime.fromtimestamp(timestamp).isoformat()
        except Exception:
            return ""
    
    def _extract_version(self, path: Path, artifact_type: str) -> str:
        """Extract version from artifact"""
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for version patterns
            import re
            version_patterns = [
                r'version["\']?\s*[:=]\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)',
                r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']',
                r'v([0-9]+\.[0-9]+\.[0-9]+)',
                r'V([0-9]+\.[0-9]+\.[0-9]+)',
            ]
            
            for pattern in version_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            # Extract from filename
            filename_match = re.search(r'v([0-9]+\.[0-9]+(?:\.[0-9]+)?)', path.name)
            if filename_match:
                return filename_match.group(1)
            
            return "unknown"
            
        except Exception:
            return "unknown"
    
    def _determine_canonical_location(self, path: Path, group: str) -> str:
        """Determine canonical location for artifact"""
        
        canonical_locations = {
            "core_engine": "core/",
            "agents": "agents/",
            "dmaic_engine": "DMAIC_V3/",
            "tools": "tools_v2.3/",
            "tests": "tests/",
            "documentation": "docs_versioned/v2.3_active/",
            "configuration": "config/",
            "cicd": ".github/workflows/",
            "legacy": "docs_versioned/v2.2_archived/"
        }
        
        canonical_base = canonical_locations.get(group, "")
        
        path_str = str(path).replace("\\", "/")
        
        if path_str.startswith(canonical_base):
            return str(path)  # Already in canonical location
        else:
            return canonical_base + path.name
    
    def _determine_actions(
        self,
        path: Path,
        artifact_type: str,
        maturity: int,
        quality: float,
        integration: str,
        canonical: str
    ) -> List[str]:
        """Determine required actions"""
        
        actions = []
        
        # Maturity actions
        if maturity < 2:
            actions.append("UPGRADE_MATURITY_TO_V2.3")
        
        # Quality actions
        if quality < 70:
            actions.append("IMPROVE_QUALITY")
        
        # Integration actions
        if integration == "standalone":
            actions.append("INTEGRATE_WITH_ORCHESTRATOR")
        
        # Location actions
        if str(path) != canonical:
            actions.append(f"MOVE_TO_CANONICAL: {canonical}")
        
        # Type-specific actions
        if artifact_type == "code:python":
            if quality < 80:
                actions.append("ADD_TESTS")
            if maturity < 2:
                actions.append("ADD_DOCSTRINGS")
                actions.append("ADD_TYPE_HINTS")
        
        return actions
    
    def _collect_metrics(self, path: Path, artifact_type: str) -> Dict:
        """Collect additional metrics"""
        
        metrics = {}
        
        try:
            # File size
            metrics['file_size_bytes'] = path.stat().st_size
            
            # Line count
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            metrics['total_lines'] = len(lines)
            metrics['non_empty_lines'] = sum(1 for line in lines if line.strip())
            
            # Code-specific metrics
            if artifact_type == "code:python":
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                metrics['functions'] = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.FunctionDef))
                metrics['classes'] = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.ClassDef))
                metrics['imports'] = len(self._extract_python_imports(path))
            
        except Exception:
            pass
        
        return metrics
    
    # ============ BATCH OPERATIONS ============
    
    def rank_all_artifacts(
        self,
        exclude_patterns: List[str] = None
    ) -> Dict[str, ArtifactRanking]:
        """Rank all artifacts in repository"""
        
        if exclude_patterns is None:
            exclude_patterns = [
                ".git",
                "__pycache__",
                "*.pyc",
                ".vs",
                ".vscode",
                "node_modules"
            ]
        
        all_files = []
        
        for root, dirs, files in os.walk(self.root_path):
            # Exclude directories
            dirs[:] = [d for d in dirs if not any(
                self._matches_pattern(d, pattern) for pattern in exclude_patterns
            )]
            
            for file in files:
                file_path = Path(root) / file
                
                # Exclude files
                if not any(self._matches_pattern(str(file_path), pattern) for pattern in exclude_patterns):
                    all_files.append(file_path)
        
        print(f"Ranking {len(all_files)} artifacts...")
        
        for i, file_path in enumerate(all_files):
            try:
                self.rank_artifact(str(file_path.relative_to(self.root_path)))
                
                if (i + 1) % 100 == 0:
                    print(f"  Ranked {i + 1}/{len(all_files)} artifacts")
                    
            except Exception as e:
                print(f"  Error ranking {file_path}: {e}")
        
        print(f"Ranking complete: {len(self.rankings)} artifacts ranked")
        
        return self.rankings
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern"""
        
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
    
    # ============ REPORTING ============
    
    def generate_ranking_report(self, output_path: str = "artifact_rankings_report.json"):
        """Generate comprehensive ranking report"""
        
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_artifacts": len(self.rankings),
            "rankings": {
                path: {
                    "type": ranking.type,
                    "group": ranking.group,
                    "function": ranking.function,
                    "maturity_level": ranking.maturity_level,
                    "integration_status": ranking.integration_status,
                    "quality_score": ranking.quality_score,
                    "priority_rank": ranking.priority_rank,
                    "actions_required": ranking.actions_required
                }
                for path, ranking in self.rankings.items()
            },
            "summary": {
                "by_type": self._summarize_by("type"),
                "by_group": self._summarize_by("group"),
                "by_maturity": self._summarize_by("maturity_level"),
                "by_priority": self._summarize_by("priority_rank")
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Ranking report saved to {output_path}")
        
        return report
    
    def _summarize_by(self, dimension: str) -> Dict:
        """Summarize rankings by dimension"""
        
        summary = {}
        
        for ranking in self.rankings.values():
            key = getattr(ranking, dimension)
            
            if key not in summary:
                summary[key] = {
                    "count": 0,
                    "avg_quality": 0.0,
                    "total_quality": 0.0
                }
            
            summary[key]["count"] += 1
            summary[key]["total_quality"] += ranking.quality_score
        
        # Calculate averages
        for key in summary:
            if summary[key]["count"] > 0:
                summary[key]["avg_quality"] = round(
                    summary[key]["total_quality"] / summary[key]["count"], 2
                )
            del summary[key]["total_quality"]
        
        return summary


# ============ COMPARATIVE RANKING ============

def compare_artifacts(
    artifact_a: ArtifactRanking,
    artifact_b: ArtifactRanking
) -> Dict:
    """Compare two artifacts"""
    
    # Calculate similarity
    similarity = 0.0
    
    if artifact_a.type == artifact_b.type:
        similarity += 25.0
    if artifact_a.group == artifact_b.group:
        similarity += 25.0
    if artifact_a.function == artifact_b.function:
        similarity += 25.0
    
    # Quality similarity
    quality_diff = abs(artifact_a.quality_score - artifact_b.quality_score)
    quality_similarity = max(0, 100 - quality_diff) * 0.25
    similarity += quality_similarity
    
    # Deltas
    quality_delta = artifact_a.quality_score - artifact_b.quality_score
    maturity_delta = artifact_a.maturity_level - artifact_b.maturity_level
    
    # Recommendation
    if similarity > 80 and artifact_a.group == artifact_b.group:
        if quality_delta > 20:
            recommendation = "keep_a_archive_b"
        elif quality_delta < -20:
            recommendation = "keep_b_archive_a"
        else:
            recommendation = "merge"
    else:
        recommendation = "keep_both"
    
    return {
        "similarity_score": round(similarity, 2),
        "quality_delta": round(quality_delta, 2),
        "maturity_delta": maturity_delta,
        "recommendation": recommendation,
        "rationale": _generate_rationale(artifact_a, artifact_b, quality_delta, maturity_delta)
    }

def _generate_rationale(a, b, quality_delta, maturity_delta) -> str:
    """Generate comparison rationale"""
    
    reasons = []
    
    if abs(quality_delta) > 20:
        better = "A" if quality_delta > 0 else "B"
        reasons.append(f"Artifact {better} has significantly better quality (+{abs(quality_delta):.1f} points)")
    
    if maturity_delta != 0:
        better = "A" if maturity_delta > 0 else "B"
        reasons.append(f"Artifact {better} is more mature (level {max(a.maturity_level, b.maturity_level)})")
    
    if a.type != b.type:
        reasons.append(f"Different types: {a.type} vs {b.type}")
    
    return "; ".join(reasons) if reasons else "Similar artifacts"


# ============ MAIN EXECUTION ============

if __name__ == "__main__":
    import sys
    import datetime
    
    print("=" * 80)
    print("ARTIFACT RANKING SYSTEM V3.0")
    print("=" * 80)
    
    engine = ArtifactRankingEngine()
    
    # Rank all artifacts
    rankings = engine.rank_all_artifacts()
    
    # Generate report
    report = engine.generate_ranking_report("artifact_rankings_report.json")
    
    # Display summary
    print("\n" + "=" * 80)
    print("RANKING SUMMARY")
    print("=" * 80)
    print(f"Total artifacts ranked: {report['total_artifacts']}")
    print("\nBy Group:")
    for group, stats in sorted(report['summary']['by_group'].items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"  {group:20s}: {stats['count']:4d} artifacts, avg quality: {stats['avg_quality']:5.1f}")
    
    print("\nBy Priority:")
    for priority, stats in report['summary']['by_priority'].items():
        print(f"  {priority:20s}: {stats['count']:4d} artifacts, avg quality: {stats['avg_quality']:5.1f}")
    
    print("\n" + "=" * 80)
    print("Report saved to: artifact_rankings_report.json")
    print("=" * 80)
```

---

## PART III: USAGE EXAMPLES

### A. Rank Single Artifact

```python
from artifact_ranking_engine import ArtifactRankingEngine

engine = ArtifactRankingEngine()

ranking = engine.rank_artifact("local_mcp/agents/analysis_cryo_dm_v2.3_OPTIMIZED.py")

print(f"Path: {ranking.path}")
print(f"Type: {ranking.type}")
print(f"Group: {ranking.group}")
print(f"Function: {ranking.function}")
print(f"Maturity: {ranking.maturity_level}")
print(f"Quality Score: {ranking.quality_score}/100")
print(f"Priority: {ranking.priority_rank}")
print(f"Actions Required: {ranking.actions_required}")
```

### B. Batch Ranking

```python
engine = ArtifactRankingEngine()

rankings = engine.rank_all_artifacts(
    exclude_patterns=[".git", "__pycache__", "*.pyc"]
)

report = engine.generate_ranking_report("artifact_rankings_report.json")
```

### C. Compare Two Artifacts

```python
from artifact_ranking_engine import compare_artifacts

engine = ArtifactRankingEngine()

artifact_a = engine.rank_artifact("local_mcp/agents/analysis_cryo_dm_v2.3_OPTIMIZED.py")
artifact_b = engine.rank_artifact("local_mcp/agents/analysis_cryo_dm_v2.1_OPTIMIZED.py")

comparison = compare_artifacts(artifact_a, artifact_b)

print(f"Similarity: {comparison['similarity_score']}%")
print(f"Quality Delta: {comparison['quality_delta']}")
print(f"Recommendation: {comparison['recommendation']}")
print(f"Rationale: {comparison['rationale']}")
```

---

## PART IV: INTEGRATION WITH DMAIC

The artifact ranking system integrates with DMAIC phases:

### Phase 1 (Define)
- Rank all artifacts to establish baseline
- Identify high-priority artifacts for refactoring

### Phase 2 (Measure)
- Track quality scores over iterations
- Measure improvement metrics

### Phase 3 (Analyze)
- Compare rankings to identify patterns
- Detect duplicate/redundant artifacts

### Phase 4 (Improve)
- Execute actions from ranking (upgrade, refactor, move)
- Re-rank to validate improvements

### Phase 5 (Control)
- Continuous ranking to maintain quality
- Alert when quality degrades

---

## APPENDIX: OUTPUT EXAMPLES

### A. Single Artifact Ranking Output

```json
{
  "path": "local_mcp/agents/analysis_cryo_dm_v2.3_OPTIMIZED.py",
  "type": "code:python",
  "group": "agents",
  "function": "execution",
  "maturity_level": 2,
  "integration_status": "fully_integrated",
  "quality_score": 92.3,
  "priority_rank": "critical",
  "dependencies": [
    "pathlib", "typing", "dataclasses", "json"
  ],
  "dependent_artifacts": [
    "orchestrator_v3.py",
    "dmaic_v3_engine.py"
  ],
  "last_modified": "2025-01-11T15:30:00",
  "version": "2.3.0",
  "canonical_location": "agents/analysis/cryo_dm_v2.3.py",
  "actions_required": [
    "I/O_TEST_WITH_ORCHESTRATOR_V3"
  ],
  "metrics": {
    "file_size_bytes": 15234,
    "total_lines": 423,
    "non_empty_lines": 378,
    "functions": 15,
    "classes": 2,
    "imports": 12
  }
}
```

### B. Summary Report Output

```json
{
  "timestamp": "2025-01-12T10:00:00",
  "total_artifacts": 342,
  "summary": {
    "by_group": {
      "agents": {"count": 12, "avg_quality": 88.5},
      "core_engine": {"count": 8, "avg_quality": 75.2},
      "tools": {"count": 15, "avg_quality": 82.1},
      "documentation": {"count": 120, "avg_quality": 72.3}
    },
    "by_priority": {
      "critical": {"count": 25, "avg_quality": 85.0},
      "high": {"count": 80, "avg_quality": 78.5},
      "medium": {"count": 150, "avg_quality": 70.2},
      "low": {"count": 87, "avg_quality": 45.8}
    }
  }
}
```

---

**END OF DOCUMENT**

**Related Documents**:
- `COMPREHENSIVE_REFACTORING_INTEGRATION_V3.0_MASTER.md` - Full 12-cluster architecture
- `DMAIC_V3_12CLUSTER_TEMPORAL_INTEGRATION_MASTER.md` - Temporal integration details

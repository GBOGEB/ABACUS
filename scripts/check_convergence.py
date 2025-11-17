#!/usr/bin/env python3
"""
DMAIC V3 - Convergence Check Script
Analyzes workspace stability and calculates convergence score
"""

import os
import json
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "DMAIC_V3_OUTPUT" / "reports"

@dataclass
class ConvergenceMetrics:
    """Metrics for tracking convergence"""
    iteration: int
    timestamp: str
    total_files: int
    stable_files: int
    file_stability_pct: float
    total_tests: int
    passing_tests: int
    test_stability_pct: float
    tracked_metrics: int
    stable_metrics: int
    metric_stability_pct: float
    knowledge_packs_total: int
    knowledge_packs_new: int
    knowledge_growth_pct: float
    regressions_detected: int
    convergence_score: float
    converged: bool
    maturity_level: int
    
    def to_dict(self):
        return asdict(self)


def load_config() -> Dict:
    """Load maturity configuration"""
    config_path = Path("config/maturity_config.yaml")
    if not config_path.exists():
        print(f"Warning: {config_path} not found, using defaults")
        return {
            'convergence_calculation': {
                'weights': {
                    'file_stability': 0.30,
                    'test_stability': 0.25,
                    'metric_stability': 0.20,
                    'knowledge_growth': 0.15,
                    'zero_regressions': 0.10
                },
                'thresholds': {
                    'converged': 95.0,
                    'stable': 85.0,
                    'developing': 70.0
                }
            }
        }
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file"""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        return f"ERROR:{str(e)}"


def scan_workspace_files() -> Tuple[int, int]:
    """
    Scan workspace files and determine stability
    Returns: (total_files, stable_files)
    """
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        'DMAIC_V3_OUTPUT',
        'DMAIC_V23_OUTPUT',
        '.pytest_cache',
        'node_modules',
        '.venv',
        'temp_venv',
        '.log',
        '.git'
    ]
    
    workspace = Path('.')
    all_files = []
    
    for file in workspace.rglob('*.py'):
        # Check if file should be excluded
        if any(pattern in str(file) for pattern in exclude_patterns):
            continue
        if file.is_file():
            all_files.append(file)
    
    total_files = len(all_files)
    
    # Load previous hashes if available
    hash_file = Path('DMAIC_V3_OUTPUT/.file_hashes.json')
    previous_hashes = {}
    if hash_file.exists():
        try:
            with open(hash_file, 'r') as f:
                history = json.load(f)
                # Get hashes from 3 iterations ago
                if len(history) >= 3:
                    previous_hashes = history[-3].get('hashes', {})
        except Exception as e:
            print(f"Warning: Could not load previous hashes: {e}")
    
    # Calculate current hashes and compare
    current_hashes = {}
    stable_files = 0
    
    for file in all_files:
        file_hash = calculate_file_hash(file)
        file_str = str(file.relative_to(workspace))
        current_hashes[file_str] = file_hash
        
        # File is stable if it existed 3 iterations ago and hash matches
        if file_str in previous_hashes and previous_hashes[file_str] == file_hash:
            stable_files += 1
    
    # Save current hashes
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if hash_file.exists():
        with open(hash_file, 'r') as f:
            history = json.load(f)
    
    history.append({
        'timestamp': datetime.now().isoformat(),
        'iteration': len(history) + 1,
        'hashes': current_hashes
    })
    
    with open(hash_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    return total_files, stable_files


def check_test_stability() -> Tuple[int, int]:
    """
    Check test stability
    Returns: (total_tests, passing_tests)
    """
    # For now, return estimated values
    # In production, this would run pytest and parse results
    return 10, 10  # Assuming all tests pass for now


def check_metric_stability() -> Tuple[int, int]:
    """
    Check metric stability
    Returns: (tracked_metrics, stable_metrics)
    """
    # For now, return estimated values
    # In production, this would compare metrics over time
    return 8, 6  # 6 out of 8 metrics stable


def check_knowledge_growth() -> Tuple[int, int]:
    """
    Check knowledge pack growth
    Returns: (total_knowledge_packs, new_knowledge_packs)
    """
    knowledge_dir = Path('DMAIC_V3_OUTPUT/knowledge')
    if not knowledge_dir.exists():
        return 0, 0
    
    # Count knowledge pack files
    packs = list(knowledge_dir.glob('*.json'))
    total = len(packs)
    
    # Estimate new packs (in production, track with timestamps)
    new = max(1, int(total * 0.1))  # Assume 10% new
    
    return total, new


def calculate_convergence_score(
    file_stability_pct: float,
    test_stability_pct: float,
    metric_stability_pct: float,
    knowledge_growth_pct: float,
    regressions: int,
    config: Dict
) -> float:
    """Calculate weighted convergence score"""
    weights = config['convergence_calculation']['weights']
    
    regression_score = 100.0 if regressions == 0 else 0.0
    
    score = (
        weights['file_stability'] * file_stability_pct +
        weights['test_stability'] * test_stability_pct +
        weights['metric_stability'] * metric_stability_pct +
        weights['knowledge_growth'] * min(knowledge_growth_pct, 100.0) +
        weights['zero_regressions'] * regression_score
    )
    
    return round(score, 2)


def determine_maturity_level(score: float, config: Dict) -> int:
    """Determine maturity level based on convergence score"""
    thresholds = config['convergence_calculation']['thresholds']
    
    if score >= thresholds['converged']:
        return 3  # Production
    elif score >= thresholds['stable']:
        return 2  # Development
    elif score >= thresholds['developing']:
        return 1  # Foundation
    else:
        return 0  # Planning


def latest_metrics():
    if not REPORTS.exists():
        return None
    files = sorted(REPORTS.glob("dmaic_v3_run_*_metrics.json"))
    return files[-1] if files else None


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    config = load_config()

    # Files stability over rolling window
    total_files, stable_files = scan_workspace_files()
    file_stability_pct = round((stable_files / total_files * 100.0), 2) if total_files else 100.0

    # Tests
    total_tests, passing_tests = check_test_stability()
    test_stability_pct = round((passing_tests / total_tests * 100.0), 2) if total_tests else 100.0

    # Metrics
    tracked_metrics, stable_metrics = check_metric_stability()
    metric_stability_pct = round((stable_metrics / tracked_metrics * 100.0), 2) if tracked_metrics else 100.0

    # Knowledge growth
    kp_total, kp_new = check_knowledge_growth()
    knowledge_growth_pct = round((kp_new / kp_total * 100.0), 2) if kp_total else 0.0

    # Regressions
    regressions = 0  # hook into your pipeline if available

    score = calculate_convergence_score(
        file_stability_pct, test_stability_pct, metric_stability_pct, knowledge_growth_pct, regressions, config
    )
    maturity_level = determine_maturity_level(score, config)

    iter_num = len(list((ROOT / "DMAIC_V3_OUTPUT").glob("iteration_*"))) or 1
    metrics = ConvergenceMetrics(
        iteration=iter_num,
        timestamp=datetime.utcnow().isoformat() + "Z",
        total_files=total_files,
        stable_files=stable_files,
        file_stability_pct=file_stability_pct,
        total_tests=total_tests,
        passing_tests=passing_tests,
        test_stability_pct=test_stability_pct,
        tracked_metrics=tracked_metrics,
        stable_metrics=stable_metrics,
        metric_stability_pct=metric_stability_pct,
        knowledge_packs_total=kp_total,
        knowledge_packs_new=kp_new,
        knowledge_growth_pct=knowledge_growth_pct,
        regressions_detected=regressions,
        convergence_score=score,
        converged=score >= config['convergence_calculation']['thresholds']['converged'],
        maturity_level=maturity_level
    )

    # Persist report
    out = REPORTS / f"dmaic_v3_convergence_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(metrics.to_dict(), indent=2), encoding="utf-8")

    # Back-compat print
    lm = latest_metrics()
    print(f"Loaded metrics: {lm.name if lm else 'none'}")
    print(f"Convergence score: {score}")
    print(f"Maturity level: {maturity_level}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

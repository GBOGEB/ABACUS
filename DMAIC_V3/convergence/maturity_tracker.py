"""
DMAIC V3.3 - Maturity Tracker
=============================================================================
Priority: M3-003 (HIGH) from CHATREADY_HANDOVER.yaml Iteration 6
=============================================================================
Tracks progress through maturity levels:
- Level 0: Initial/Chaotic
- Level 1: Repeatable
- Level 2: Defined
- Level 3: Managed
- Level 4: Optimizing
- Level 5: Production-Ready

Features:
- Read maturity_config.yaml and task_definitions.yaml
- Calculate completion percentage per level
- Validate convergence criteria met
- Generate maturity reports
- CLI and programmatic interfaces
=============================================================================
"""

import json
from pathlib import Path
from typing import List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field


@dataclass
class MaturityLevel:
    """Maturity level definition"""

    level: int
    name: str
    description: str
    criteria: List[str]
    convergence_min: int
    tasks_required: List[str]


@dataclass
class MaturityAssessment:
    """Maturity assessment result"""

    current_level: int
    current_level_name: str
    completion_percentage: float
    overall_completion: float
    next_level: Optional[int]
    next_milestone: str
    convergence_score: float
    levels: List["MaturityLevelStatus"]
    tasks_completed: List[str]
    tasks_pending: List[str]
    blockers: List[str]
    recommendations: List[str]
    timestamp: str
    score_history: List[Any] = field(default_factory=list)  # [{timestamp, convergence_score}, ...]


@dataclass
class MaturityLevelStatus:
    """Per-level maturity progress."""

    level: int
    name: str
    completion_percentage: float
    status: str
    convergence_achieved: bool


@dataclass
class MaturityLevelStatus:
    """Per-level maturity progress."""

    level: int
    name: str
    completion_percentage: float
    status: str
    convergence_achieved: bool


class MaturityTracker:
    """
    Tracks system maturity progression through defined levels

    Uses:
    - maturity_config.yaml: Level definitions
    - task_definitions.yaml: Task tracking
    - convergence_report.json: Convergence metrics
    - planning_matrix.json: Completion tracking
    """

    MATURITY_LEVELS = {
        0: MaturityLevel(
            level=0,
            name="Initial/Chaotic",
            description="Ad-hoc processes, no formal structure",
            criteria=["Basic file structure exists", "Core agents identified"],
            convergence_min=0,
            tasks_required=[],
        ),
        1: MaturityLevel(
            level=1,
            name="Repeatable",
            description="Basic processes can be repeated",
            criteria=[
                "Phase 0 initialization works",
                "Phase 1 Define implemented",
                "Basic file scanning operational",
            ],
            convergence_min=30,
            tasks_required=["phase0_init", "phase1_define"],
        ),
        2: MaturityLevel(
            level=2,
            name="Defined",
            description="Processes are documented and standardized",
            criteria=[
                "All 5 DMAIC phases implemented",
                "Idempotency system working",
                "Planning matrix tracking",
                "Documentation complete",
            ],
            convergence_min=50,
            tasks_required=[
                "phase0_init",
                "phase1_define",
                "phase2_measure",
                "phase3_analyze",
                "phase4_improve",
                "phase5_control",
            ],
        ),
        3: MaturityLevel(
            level=3,
            name="Managed",
            description="Processes are measured and controlled",
            criteria=[
                "Phase 6 Knowledge working",
                "Ranking system operational",
                "Recursive self-ranking",
                "Convergence tracking automated",
                "Git integration working",
            ],
            convergence_min=65,
            tasks_required=[
                "phase6_knowledge",
                "ranking_system",
                "recursive_ranking",
                "convergence_analyzer",
            ],
        ),
        4: MaturityLevel(
            level=4,
            name="Optimizing",
            description="Continuous improvement processes active",
            criteria=[
                "Phase 7 Advanced Analytics",
                "Maturity tracking",
                "Stability monitoring",
                "Automated optimization",
                "Historic trend analysis",
            ],
            convergence_min=80,
            tasks_required=[
                "phase7_analytics",
                "maturity_tracker",
                "stability_monitor",
                "git_manager",
            ],
        ),
        5: MaturityLevel(
            level=5,
            name="Production-Ready",
            description="Optimized, self-improving system",
            criteria=[
                "Phase 8 Recursive Optimization",
                "100% test coverage",
                "Zero critical issues",
                "Full CI/CD pipeline",
                "Production deployment",
            ],
            convergence_min=95,
            tasks_required=[
                "phase8_optimization",
                "ci_cd_pipeline",
                "production_deployment",
            ],
        ),
    }

    def __init__(self, workspace_root: Path = Path(".")):
        self.workspace_root = workspace_root
        self.maturity_file = workspace_root / "maturity_assessment.json"
        self.convergence_file = workspace_root / "convergence_report.json"
        self.planning_file = workspace_root / "planning_matrix.json"

    @property
    def workspace_path(self) -> Path:
        """Alias for workspace_root for backward compatibility"""
        return self.workspace_root

    def assess_current_maturity(self) -> MaturityAssessment:
        """
        Assess current system maturity level

        Returns:
            MaturityAssessment with current state
        """
        # Load convergence score
        convergence_score = self._load_convergence_score()

        # Load completed tasks
        completed_tasks = self._load_completed_tasks()

        # Determine current level
        current_level = self._determine_level(convergence_score, completed_tasks)
        current_level_def = self.MATURITY_LEVELS[current_level]

        # Calculate completion for current level
        completion = self._calculate_level_completion(current_level, completed_tasks)

        # Determine next level
        next_level = current_level + 1 if current_level < 5 else None
        next_milestone = (
            f"Level {next_level} - {self.MATURITY_LEVELS[next_level].name}"
            if next_level is not None
            else "Production-ready"
        )

        # Identify pending tasks for current level
        pending_tasks = [
            task
            for task in current_level_def.tasks_required
            if task not in completed_tasks
        ]

        # Identify blockers
        blockers = self._identify_blockers(
            current_level, convergence_score, pending_tasks
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            current_level, convergence_score, pending_tasks, blockers
        )

        level_statuses = self._build_level_statuses(
            current_level, convergence_score, completed_tasks
        )
        overall_completion = round(
            sum(level.completion_percentage for level in level_statuses)
            / len(level_statuses),
            2,
        )

        assessment = MaturityAssessment(
            current_level=current_level,
            current_level_name=current_level_def.name,
            completion_percentage=completion,
            overall_completion=overall_completion,
            next_level=next_level,
            next_milestone=next_milestone,
            convergence_score=convergence_score,
            levels=level_statuses,
            tasks_completed=completed_tasks,
            tasks_pending=pending_tasks,
            blockers=blockers,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat(),
        )

        # Save assessment
        self._save_assessment(assessment)

        return assessment

    def _build_level_statuses(
        self, current_level: int, convergence_score: float, completed_tasks: List[str]
    ) -> List[MaturityLevelStatus]:
        """Build progress snapshots for all maturity levels."""
        statuses = []

        for level, level_def in self.MATURITY_LEVELS.items():
            completion = self._calculate_level_completion(level, completed_tasks)
            convergence_achieved = convergence_score >= level_def.convergence_min

            if level < current_level:
                status = "COMPLETED"
                completion = 100.0
            elif level == current_level:
                status = "ACTIVE" if completion < 100 else "COMPLETED"
            else:
                status = "PENDING"

            statuses.append(
                MaturityLevelStatus(
                    level=level,
                    name=level_def.name,
                    completion_percentage=completion,
                    status=status,
                    convergence_achieved=convergence_achieved,
                )
            )

        return statuses

    def _load_convergence_score(self) -> float:
        """Load convergence score from report"""
        if not self.convergence_file.exists():
            return 0.0

        try:
            with open(self.convergence_file, "r") as f:
                data = json.load(f)
            return float(data.get("score", 0))
        except:
            return 0.0

    def _load_completed_tasks(self) -> List[str]:
        """Load list of completed tasks"""
        completed = []

        # Check for completed phases in output directory
        output_dir = Path("DMAIC_V3_OUTPUT")
        if output_dir.exists():
            # Find latest iteration
            iterations = sorted(output_dir.glob("iteration_*"))
            if iterations:
                latest = iterations[-1]

                # Check which phases exist
                for phase_num in range(7):
                    phase_name = f"phase{phase_num}"
                    phase_dir = latest / phase_name
                    if phase_dir.exists() and list(phase_dir.glob("*.json")):
                        completed.append(phase_name if phase_num > 0 else "phase0_init")

        # Check for other components
        if Path("DMAIC_V3/core/idempotency_wrapper.py").exists():
            completed.append("idempotency_system")

        if (
            Path("ranking.json").exists()
            or Path("GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml").exists()
        ):
            completed.append("ranking_system")

        if Path("recursive_self_ranking_system.py").exists():
            completed.append("recursive_ranking")

        if self.convergence_file.exists():
            completed.append("convergence_analyzer")

        if Path("DMAIC_V3/convergence/maturity_tracker.py").exists():
            completed.append("maturity_tracker")

        return completed

    def _determine_level(self, convergence: float, completed: List[str]) -> int:
        """Determine current maturity level"""
        for level in range(5, -1, -1):
            level_def = self.MATURITY_LEVELS[level]

            # Check convergence requirement
            if convergence < level_def.convergence_min:
                continue

            # Check task requirements
            tasks_met = all(task in completed for task in level_def.tasks_required)
            if tasks_met:
                return level

        return 0

    def _calculate_level_completion(self, level: int, completed: List[str]) -> float:
        """Calculate completion percentage for current level"""
        level_def = self.MATURITY_LEVELS[level]

        if not level_def.tasks_required:
            return 100.0

        completed_count = sum(
            1 for task in level_def.tasks_required if task in completed
        )
        total_count = len(level_def.tasks_required)

        return round((completed_count / total_count) * 100, 2)

    def _identify_blockers(
        self, level: int, convergence: float, pending: List[str]
    ) -> List[str]:
        """Identify blockers preventing progression"""
        blockers = []

        level_def = self.MATURITY_LEVELS[level]

        # Check convergence blocker
        if convergence < level_def.convergence_min:
            blockers.append(
                f"Convergence score ({convergence}) below minimum ({level_def.convergence_min})"
            )

        # Check task blockers
        if pending:
            blockers.append(f"{len(pending)} tasks pending: {', '.join(pending[:3])}")

        return blockers

    def _generate_recommendations(
        self, level: int, convergence: float, pending: List[str], blockers: List[str]
    ) -> List[str]:
        """Generate recommendations for progression"""
        recs = []

        if blockers:
            recs.append("Address blockers listed above")

        if pending:
            recs.append(f"Complete pending tasks: {', '.join(pending[:3])}")

        level_def = self.MATURITY_LEVELS[level]
        next_level = level + 1

        if level < 5:
            next_def = self.MATURITY_LEVELS[next_level]
            recs.append(
                f"Target Level {next_level} ({next_def.name}) - Convergence: {next_def.convergence_min}+"
            )

        if convergence < 80:
            recs.append("Focus on improving convergence metrics")

        return recs

    def _save_assessment(self, assessment: MaturityAssessment):
        """Save assessment to file, appending to score_history for trend tracking."""
        # Load existing history if file exists
        history = []
        if self.maturity_file.exists():
            try:
                with open(self.maturity_file, "r") as f:
                    existing = json.load(f)
                history = existing.get("score_history") or []
            except Exception:
                history = []

        # Append this run's snapshot to history only when metrics change.
        snapshot = {
            "timestamp": assessment.timestamp,
            "convergence_score": assessment.convergence_score,
            "current_level": assessment.current_level,
            "overall_completion": assessment.overall_completion,
        }
        if not history:
            history.append(snapshot)
        else:
            last = history[-1]
            same_metrics = (
                last.get("convergence_score") == snapshot["convergence_score"]
                and last.get("current_level") == snapshot["current_level"]
                and last.get("overall_completion") == snapshot["overall_completion"]
            )
            if same_metrics:
                history[-1]["timestamp"] = snapshot["timestamp"]
            else:
                history.append(snapshot)
        history = history[-50:]

        data = asdict(assessment)
        data["score_history"] = history
        with open(self.maturity_file, "w") as f:
            json.dump(data, f, indent=2)

    def generate_report(self) -> MaturityAssessment:
        """Generate the current maturity assessment."""
        return self.assess_current_maturity()

    def generate_text_report(self) -> str:
        """Generate human-readable maturity report."""
        assessment = self.assess_current_maturity()

        report = []
        report.append("=" * 80)
        report.append("DMAIC V3.3 - MATURITY ASSESSMENT REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {assessment.timestamp}")
        report.append("")

        report.append(
            f"CURRENT LEVEL: {assessment.current_level} - {assessment.current_level_name}"
        )
        report.append(f"Completion: {assessment.completion_percentage}%")
        report.append(f"Convergence Score: {assessment.convergence_score}/100")
        report.append("")

        if assessment.next_level is not None:
            next_def = self.MATURITY_LEVELS[assessment.next_level]
            report.append(f"NEXT LEVEL: {assessment.next_level} - {next_def.name}")
            report.append(f"Requirements: Convergence {next_def.convergence_min}+")
            report.append("")

        report.append("TASKS COMPLETED:")
        for task in assessment.tasks_completed[:10]:
            report.append(f"  [+] {task}")
        if len(assessment.tasks_completed) > 10:
            report.append(f"  ... and {len(assessment.tasks_completed) - 10} more")
        report.append("")

        if assessment.tasks_pending:
            report.append("TASKS PENDING:")
            for task in assessment.tasks_pending:
                report.append(f"  [ ] {task}")
            report.append("")

        if assessment.blockers:
            report.append("BLOCKERS:")
            for blocker in assessment.blockers:
                report.append(f"  [!] {blocker}")
            report.append("")

        if assessment.recommendations:
            report.append("RECOMMENDATIONS:")
            for idx, rec in enumerate(assessment.recommendations, 1):
                report.append(f"  {idx}. {rec}")

        report.append("=" * 80)

        return "\n".join(report)


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="DMAIC V3.3 Maturity Tracker")
    parser.add_argument(
        "--workspace", type=str, default=".", help="Workspace root directory"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    tracker = MaturityTracker(workspace_root=Path(args.workspace))

    if args.json:
        assessment = tracker.assess_current_maturity()
        print(json.dumps(asdict(assessment), indent=2))
    else:
        print(tracker.generate_text_report())


if __name__ == "__main__":
    main()

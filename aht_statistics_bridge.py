"""AHT statistics bridge backed by bootstrap evaluation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from bootstrap_eval import bootstrap_ci_diff_means, bootstrap_ci_mean


class AHTStatisticsBridge:
    """Persisted hypothesis-testing bridge for ABACUS learning loops."""

    def __init__(
        self,
        learnings_db_path: Path | str | None = None,
        aht_log_path: Path | str | None = None,
    ) -> None:
        self.learnings_db_path = Path(learnings_db_path or "aht_learnings.json")
        self.aht_log_path = Path(aht_log_path or "aht_statistics.log")
        self.learnings_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.aht_log_path.parent.mkdir(parents=True, exist_ok=True)

    def test_hypothesis_with_bootstrap(
        self,
        hypothesis: str,
        observed_data: Iterable[float],
        expected_value: float | None = None,
        reference_group: Iterable[float] | None = None,
        alpha: float = 0.05,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        observed = np.asarray(list(observed_data), dtype=float)
        observed = observed[~np.isnan(observed)]
        obs_low, obs_high, _ = bootstrap_ci_mean(observed, alpha=alpha)
        result: dict[str, Any] = {
            "hypothesis": hypothesis,
            "alpha": alpha,
            "context": context or {},
            "observed": {
                "n": int(observed.size),
                "mean": float(observed.mean()) if observed.size else float("nan"),
                "std": float(observed.std(ddof=1)) if observed.size > 1 else 0.0,
                "ci_bootstrap_lower": obs_low,
                "ci_bootstrap_upper": obs_high,
            },
        }
        if reference_group is not None:
            reference = np.asarray(list(reference_group), dtype=float)
            reference = reference[~np.isnan(reference)]
            diff, low, high = bootstrap_ci_diff_means(observed, reference, alpha=alpha)
            includes_zero = bool(low <= 0 <= high)
            result["reference"] = {
                "n": int(reference.size),
                "mean": float(reference.mean()) if reference.size else float("nan"),
            }
            result["comparison"] = {
                "diff_mean": diff,
                "ci_lower": low,
                "ci_upper": high,
                "includes_zero": includes_zero,
            }
            result["status"] = "INCONCLUSIVE" if includes_zero else "SUPPORTED"
        else:
            if expected_value is None:
                raise ValueError("expected_value or reference_group is required")
            mean = result["observed"]["mean"]
            lower = result["observed"]["ci_bootstrap_lower"]
            upper = result["observed"]["ci_bootstrap_upper"]
            std = result["observed"]["std"]
            n = result["observed"]["n"]
            standard_error = std / np.sqrt(n) if n else 0.0
            boundary_tolerance = 2.0 * standard_error
            near_expected = abs(mean - expected_value) <= boundary_tolerance
            if lower > expected_value:
                result["status"] = "EXCEEDED"
            elif mean >= expected_value or lower <= expected_value <= upper or near_expected:
                result["status"] = "SUPPORTED"
            else:
                result["status"] = "REJECTED"
                result["deviation"] = float(mean - expected_value)
            result["conclusion"] = result["status"]
        self._append_learning(result)
        return result

    def load_learnings(self) -> list[dict[str, Any]]:
        if not self.learnings_db_path.exists():
            return []
        return json.loads(self.learnings_db_path.read_text(encoding="utf-8"))

    def classify_failed_check_threshold(
        self,
        *,
        repository: str,
        pull_request: str,
        head_sha: str,
        successful_checks: int,
        failed_checks: int,
        action_required_checks: int = 0,
        threshold_failed_checks: int = 1,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Embed CI failure-threshold status using the AHT learning format."""
        total_decisive = successful_checks + failed_checks + action_required_checks
        blocker_checks = failed_checks + action_required_checks
        failure_rate = blocker_checks / total_decisive if total_decisive else 0.0
        threshold_reached = blocker_checks >= threshold_failed_checks
        result = {
            "hypothesis": "PR head remains below failed-check control threshold",
            "repository": repository,
            "pull_request": pull_request,
            "head_sha": head_sha,
            "threshold": {
                "failed_or_action_required_checks": threshold_failed_checks,
                "reached": threshold_reached,
            },
            "observed": {
                "successful_checks": successful_checks,
                "failed_checks": failed_checks,
                "action_required_checks": action_required_checks,
                "blocker_checks": blocker_checks,
                "total_decisive_checks": total_decisive,
                "failure_rate": failure_rate,
            },
            "status": "THRESHOLD_BREACHED" if threshold_reached else "SUPPORTED",
            "context": context or {},
        }
        self._append_learning(result)
        return result

    def _append_learning(self, result: dict[str, Any]) -> None:
        learnings = self.load_learnings()
        learnings.append(result)
        self.learnings_db_path.write_text(
            json.dumps(learnings, indent=2, default=str),
            encoding="utf-8",
        )
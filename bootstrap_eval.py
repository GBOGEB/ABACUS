"""Bootstrap evaluation helpers for ABACUS statistical tests."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def _rng(random_state: int | None = None) -> np.random.Generator:
    return np.random.default_rng(random_state)


def bootstrap_ci_mean(
    data: Iterable[float],
    alpha: float = 0.05,
    n_bootstrap: int = 1000,
    random_state: int | None = None,
) -> tuple[float, float, np.ndarray]:
    values = np.asarray(list(data), dtype=float)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return float("nan"), float("nan"), np.asarray([])
    generator = _rng(random_state)
    samples = generator.choice(values, size=(n_bootstrap, values.size), replace=True)
    boot_means = samples.mean(axis=1)
    low = float(np.percentile(boot_means, 100 * alpha / 2))
    high = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return low, high, boot_means


def bootstrap_ci_diff_means(
    group_a: Iterable[float],
    group_b: Iterable[float],
    alpha: float = 0.05,
    n_bootstrap: int = 1000,
    random_state: int | None = None,
) -> tuple[float, float, float]:
    a_values = np.asarray(list(group_a), dtype=float)
    b_values = np.asarray(list(group_b), dtype=float)
    a_values = a_values[~np.isnan(a_values)]
    b_values = b_values[~np.isnan(b_values)]
    if a_values.size == 0 or b_values.size == 0:
        return float("nan"), float("nan"), float("nan")
    diff_hat = float(a_values.mean() - b_values.mean())
    generator = _rng(random_state)
    a_samples = generator.choice(a_values, size=(n_bootstrap, a_values.size), replace=True)
    b_samples = generator.choice(b_values, size=(n_bootstrap, b_values.size), replace=True)
    diffs = a_samples.mean(axis=1) - b_samples.mean(axis=1)
    low = float(np.percentile(diffs, 100 * alpha / 2))
    high = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    return diff_hat, low, high


def normal_ci_mean(data: Iterable[float], alpha: float = 0.05) -> tuple[float, float]:
    values = np.asarray(list(data), dtype=float)
    values = values[~np.isnan(values)]
    if values.size < 2:
        return float("nan"), float("nan")
    # Approximate z critical values for common confidence levels.
    z_value = 2.575829 if alpha <= 0.01 else 1.959964
    stderr = values.std(ddof=1) / np.sqrt(values.size)
    mean = values.mean()
    return float(mean - z_value * stderr), float(mean + z_value * stderr)


def sanitize_name(name: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in name)


def load_from_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"group", "score"}
    if not required <= set(frame.columns):
        raise ValueError("CSV must contain columns: group, score")
    frame = frame.copy()
    frame["score"] = pd.to_numeric(frame["score"], errors="coerce")
    return frame.dropna(subset=["group", "score"])


def load_from_folders(root: Path, ext: str = ".txt") -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for group_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for score_file in sorted(group_dir.glob(f"*{ext}")):
            try:
                score = float(score_file.read_text(encoding="utf-8").strip())
            except ValueError:
                continue
            rows.append({"group": group_dir.name, "score": score})
    if not rows:
        raise ValueError("No scores found")
    return pd.DataFrame(rows)


def analyse_group(name: str, scores: Iterable[float], out_dir: Path, alpha: float = 0.05) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    values = np.asarray(list(scores), dtype=float)
    values = values[~np.isnan(values)]
    ci_norm_low, ci_norm_high = normal_ci_mean(values, alpha=alpha)
    ci_boot_low, ci_boot_high, _ = bootstrap_ci_mean(values, alpha=alpha)
    plot_path = out_dir / f"{sanitize_name(name)}.txt"
    plot_path.write_text("plot placeholder\n", encoding="utf-8")
    return {
        "name": name,
        "n": int(values.size),
        "mean": float(values.mean()) if values.size else float("nan"),
        "std": float(values.std(ddof=1)) if values.size > 1 else float("nan"),
        "ci_norm_low": ci_norm_low,
        "ci_norm_high": ci_norm_high,
        "ci_boot_low": ci_boot_low,
        "ci_boot_high": ci_boot_high,
        "plot_path": str(plot_path),
    }


def run_analysis(frame: pd.DataFrame, alpha: float = 0.05, out_dir: Path | str = "output") -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "# Bootstrap Evaluation Report",
        "",
        "## Overall",
        f"Rows: {len(frame)}",
        "",
        "## Per-group Statistics",
    ]
    groups = {
        group: data["score"].to_numpy(dtype=float)
        for group, data in frame.groupby("group")
    }
    for group, values in groups.items():
        result = analyse_group(str(group), values, out_path, alpha=alpha)
        report_lines.append(f"- {group}: n={result['n']} mean={result['mean']:.3f}")
    report_lines.extend(["", "## Pairwise Group Comparisons"])
    for left, right in combinations(groups, 2):
        diff, low, high = bootstrap_ci_diff_means(groups[left], groups[right], alpha=alpha)
        report_lines.append(f"- {left} vs {right}: diff={diff:.3f} ci=[{low:.3f}, {high:.3f}]")
    (out_path / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

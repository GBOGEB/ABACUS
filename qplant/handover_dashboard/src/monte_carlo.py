"""Monte Carlo cost sensitivity analysis for helium & valve systems.

Runs 10,000 iterations with triangular He price distribution,
normal valve failure rates, and geopolitical risk scenarios.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Any

# ── Seed for reproducibility ──
RNG = np.random.default_rng(42)

# ── Helium price distribution (triangular) ──
# NOTE: Using €/kg (not €k/kg). Industry helium ~€30-300/kg range.
HE_PRICE_MIN = 117.0       # €/kg  (€70,000 / 600 kg)
HE_PRICE_MODE = 120.0      # €/kg  (most likely - current market)
HE_PRICE_MAX = 300.0       # €/kg  (crisis scenario)

N_SIMULATIONS = 10_000

@dataclass
class ValveFleet:
    """Represents a valve population segment."""
    segment: str
    count: int
    leak_rate_mbar_l_s: float
    temperature_k: float
    pressure_bar_abs: float
    mtbf_hours: float = 60_000.0       # mean time between failures
    mttr_hours: float = 4.0             # mean time to repair
    replacement_cost_eur: float = 5_000.0
    mtbf_std: float = 10_000.0          # std dev for MTBF variation

@dataclass
class ScenarioConfig:
    """Monte Carlo scenario parameters."""
    name: str
    description: str
    fleet: List[ValveFleet]
    he_price_min: float = HE_PRICE_MIN
    he_price_mode: float = HE_PRICE_MODE
    he_price_max: float = HE_PRICE_MAX
    geopolitical_disruption_prob: float = 0.0
    geopolitical_price_multiplier: float = 2.5
    mttr_multiplier: float = 1.0
    failure_rate_multiplier: float = 1.0
    operating_hours_per_year: float = 8_000.0

def _he_mass_loss_kg_year(leak_rate: float, temp_k: float, press_bar: float, count: int) -> float:
    """Calculate annual He mass loss for a valve segment using ideal gas."""
    R = 8.314462618
    M_He = 4.002602e-3  # kg/mol
    q_pa_m3_s = leak_rate * 0.1  # mbar·L/s -> Pa·m³/s
    n_dot = (q_pa_m3_s * press_bar) / (R * temp_k)
    m_dot_kg_s = n_dot * M_He
    seconds_per_year = 365.25 * 86400
    return m_dot_kg_s * seconds_per_year * count

def run_monte_carlo(config: ScenarioConfig, n_runs: int = N_SIMULATIONS) -> pd.DataFrame:
    """Run Monte Carlo simulation returning per-run results."""
    results = []
    for i in range(n_runs):
        # ── Sample helium price ──
        he_price = RNG.triangular(config.he_price_min, config.he_price_mode, config.he_price_max)
        
        # ── Geopolitical disruption ──
        geo_event = RNG.random() < config.geopolitical_disruption_prob
        if geo_event:
            he_price *= config.geopolitical_price_multiplier
        
        total_he_loss_kg = 0.0
        total_replacement_cost = 0.0
        total_downtime_hours = 0.0
        total_failures = 0
        
        for seg in config.fleet:
            # ── He mass loss ──
            he_loss = _he_mass_loss_kg_year(
                seg.leak_rate_mbar_l_s, seg.temperature_k, seg.pressure_bar_abs, seg.count
            )
            # Add ±20% variation
            he_loss *= RNG.uniform(0.8, 1.2)
            total_he_loss_kg += he_loss
            
            # ── Valve failures (Poisson from MTBF) ──
            mtbf_sample = max(1000, RNG.normal(seg.mtbf_hours, seg.mtbf_std))
            mtbf_sample /= config.failure_rate_multiplier
            failure_rate = config.operating_hours_per_year / mtbf_sample
            n_failures = RNG.poisson(failure_rate * seg.count)
            total_failures += n_failures
            
            # ── Replacement cost with ±20% variation ──
            cost_per = seg.replacement_cost_eur * RNG.uniform(0.8, 1.2)
            total_replacement_cost += n_failures * cost_per
            
            # ── Downtime ──
            mttr = seg.mttr_hours * config.mttr_multiplier
            total_downtime_hours += n_failures * mttr
        
        # ── Costs ──
        he_cost = total_he_loss_kg * he_price
        total_cost = he_cost + total_replacement_cost
        
        # ── Beam availability impact ──
        beam_hours_year = config.operating_hours_per_year
        availability = max(0, (beam_hours_year - total_downtime_hours) / beam_hours_year * 100)
        
        results.append({
            "run": i,
            "he_price_eur_kg": he_price,
            "geopolitical_event": geo_event,
            "total_he_loss_kg": total_he_loss_kg,
            "he_cost_eur": he_cost,
            "total_failures": total_failures,
            "replacement_cost_eur": total_replacement_cost,
            "total_cost_eur": total_cost,
            "downtime_hours": total_downtime_hours,
            "beam_availability_pct": availability,
        })
    
    return pd.DataFrame(results)


def compute_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute summary statistics from Monte Carlo results."""
    stats = {}
    for col in ["total_cost_eur", "he_cost_eur", "replacement_cost_eur", 
                 "total_he_loss_kg", "downtime_hours", "beam_availability_pct"]:
        vals = df[col]
        stats[col] = {
            "mean": float(vals.mean()),
            "std": float(vals.std()),
            "p10": float(vals.quantile(0.10)),
            "p25": float(vals.quantile(0.25)),
            "p50": float(vals.quantile(0.50)),
            "p75": float(vals.quantile(0.75)),
            "p90": float(vals.quantile(0.90)),
            "p95": float(vals.quantile(0.95)),
            "min": float(vals.min()),
            "max": float(vals.max()),
        }
    stats["n_runs"] = len(df)
    stats["geo_event_pct"] = float(df["geopolitical_event"].mean() * 100)
    return stats


def sensitivity_tornado(df: pd.DataFrame, config: ScenarioConfig) -> pd.DataFrame:
    """Compute sensitivity of total cost to each input variable."""
    base_cost = df["total_cost_eur"].median()
    
    sensitivities = []
    
    # He price sensitivity
    low_he = df[df["he_price_eur_kg"] <= df["he_price_eur_kg"].quantile(0.1)]["total_cost_eur"].median()
    high_he = df[df["he_price_eur_kg"] >= df["he_price_eur_kg"].quantile(0.9)]["total_cost_eur"].median()
    sensitivities.append({"variable": "Helium Price (€/kg)", "low": low_he, "high": high_he, "base": base_cost})
    
    # Failure count sensitivity
    low_f = df[df["total_failures"] <= df["total_failures"].quantile(0.1)]["total_cost_eur"].median()
    high_f = df[df["total_failures"] >= df["total_failures"].quantile(0.9)]["total_cost_eur"].median()
    sensitivities.append({"variable": "Valve Failures (#/yr)", "low": low_f, "high": high_f, "base": base_cost})
    
    # He loss sensitivity
    low_l = df[df["total_he_loss_kg"] <= df["total_he_loss_kg"].quantile(0.1)]["total_cost_eur"].median()
    high_l = df[df["total_he_loss_kg"] >= df["total_he_loss_kg"].quantile(0.9)]["total_cost_eur"].median()
    sensitivities.append({"variable": "He Loss (kg/yr)", "low": low_l, "high": high_l, "base": base_cost})
    
    # Downtime sensitivity
    low_d = df[df["downtime_hours"] <= df["downtime_hours"].quantile(0.1)]["total_cost_eur"].median()
    high_d = df[df["downtime_hours"] >= df["downtime_hours"].quantile(0.9)]["total_cost_eur"].median()
    sensitivities.append({"variable": "Downtime (hrs/yr)", "low": low_d, "high": high_d, "base": base_cost})
    
    # Geopolitical sensitivity
    no_geo = df[~df["geopolitical_event"]]["total_cost_eur"].median()
    yes_geo = df[df["geopolitical_event"]]["total_cost_eur"].median() if df["geopolitical_event"].any() else base_cost
    sensitivities.append({"variable": "Geopolitical Disruption", "low": no_geo, "high": yes_geo, "base": base_cost})
    
    sdf = pd.DataFrame(sensitivities)
    sdf["range"] = sdf["high"] - sdf["low"]
    return sdf.sort_values("range", ascending=True)


# ── Pre-built scenarios ──

def build_baseline_fleet() -> List[ValveFleet]:
    return [
        ValveFleet("Cold high-integrity", 150, 1e-5, 4, 12, 60000, 4, 8900, 10000),
        ValveFleet("Cold seat-leak tail", 60, 1e-4, 4, 12, 40000, 6, 8900, 8000),
        ValveFleet("Warm process (Meca Inox)", 180, 1e-5, 300, 5, 80000, 2, 4200, 15000),
        ValveFleet("Warm seat class", 20, 1e-4, 300, 5, 50000, 3, 4700, 10000),
    ]

SCENARIOS = {
    "baseline": ScenarioConfig(
        name="Baseline",
        description="Standard operations, expected helium price, normal failure rates",
        fleet=build_baseline_fleet(),
    ),
    "geopolitical": ScenarioConfig(
        name="Geopolitical Crisis",
        description="Iran conflict → helium supply disruption, 30% disruption probability",
        fleet=build_baseline_fleet(),
        geopolitical_disruption_prob=0.30,
        geopolitical_price_multiplier=2.5,
    ),
    "supply_chain": ScenarioConfig(
        name="Supply Chain Disruption",
        description="Longer MTTR (8h vs 4h baseline), extended repair times",
        fleet=build_baseline_fleet(),
        mttr_multiplier=2.0,
    ),
    "accelerated_failure": ScenarioConfig(
        name="Accelerated Failure",
        description="Higher leak rates → more frequent replacement, 1.5x failure rate",
        fleet=build_baseline_fleet(),
        failure_rate_multiplier=1.5,
    ),
}


def run_all_scenarios() -> Dict[str, Dict[str, Any]]:
    """Run all scenarios and return results + statistics."""
    all_results = {}
    for key, config in SCENARIOS.items():
        df = run_monte_carlo(config)
        stats = compute_statistics(df)
        tornado = sensitivity_tornado(df, config)
        all_results[key] = {
            "config": config,
            "df": df,
            "stats": stats,
            "tornado": tornado,
        }
    return all_results

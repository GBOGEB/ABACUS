"""Risk & operations modeling for QPLANT cryogenic systems.

Models geopolitical risks, operational scenarios, and beam availability impact.
"""
from __future__ import annotations
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class RiskItem:
    id: str
    category: str
    title: str
    description: str
    likelihood: int      # 1-5
    impact: int          # 1-5
    risk_score: int      # likelihood × impact
    mitigation: str
    status: str          # OPEN, MITIGATED, ACCEPTED, MONITOR
    owner: str

RISK_REGISTER: List[RiskItem] = [
    RiskItem("RISK-001", "Geopolitical", "Iran Conflict → Helium Supply",
             "Military escalation disrupts Qatar/Iran helium production (30% global supply). "
             "Algeria and US sources insufficient to cover shortfall. Price spike 2-3x.",
             4, 5, 20, "Strategic helium reserve (3-month buffer), dual-source contracts, "
             "helium recovery system optimization", "MONITOR", "Procurement"),
    RiskItem("RISK-002", "Geopolitical", "LNG/LPG Market Coupling",
             "Helium is byproduct of LNG processing. LNG market disruption cascades to He supply.",
             3, 4, 12, "Monitor LNG futures, establish He-specific supply agreements decoupled from LNG spot",
             "MONITOR", "Procurement"),
    RiskItem("RISK-003", "Operational", "LOOP Event (Loss of Instrument Air)",
             "Loss of compressed air supply causes all pneumatic valves to fail-safe position. "
             "QPLANT trip, proton beam shutdown.",
             2, 5, 10, "Backup air supply (accumulator tank), fail-safe valve positions verified, "
             "LOOP recovery procedure tested annually", "MITIGATED", "Operations"),
    RiskItem("RISK-004", "Operational", "Cascade Valve Failure",
             "Single valve leak increases system pressure → accelerates wear on adjacent valves → cascade.",
             2, 4, 8, "Pressure relief valves, leak monitoring system, predictive maintenance schedule",
             "MITIGATED", "Engineering"),
    RiskItem("RISK-005", "Supply Chain", "Extended MTTR (Spare Parts)",
             "Vendor lead times extend from 4h to 8h+ due to supply chain disruption (post-COVID effects).",
             3, 3, 9, "On-site spare inventory (10% cold, 5% warm), multiple qualified suppliers",
             "ACCEPTED", "Maintenance"),
    RiskItem("RISK-006", "Technical", "Warm Valve Leak Rate Derogation",
             "Meca Inox valves do NOT meet 1×10⁻⁹ mbar·l/s spec. Higher He losses to ambient accepted.",
             3, 3, 9, "GBO calculation to verify acceptable loss rate, new sub-class with higher allowable rate, "
             "evaluate Cryoworld variants", "OPEN", "Engineering"),
    RiskItem("RISK-007", "Technical", "Seal Degradation under Radiation",
             "HDPE/UHMWPE seals may degrade faster under sustained radiation exposure.",
             2, 3, 6, "Radiation testing program, preventive seal replacement at PM intervals",
             "MONITOR", "Engineering"),
    RiskItem("RISK-008", "Financial", "Helium Price Volatility",
             "Market helium price fluctuates €117-300/kg. Budget uncertainty for annual operations.",
             4, 3, 12, "Monte Carlo cost modeling, budget contingency at P90, hedging contracts",
             "ACCEPTED", "Finance"),
    RiskItem("RISK-009", "Regulatory", "ASME/PED Compliance Gap",
             "Valve derogation from leak spec may conflict with pressure equipment directive.",
             2, 4, 8, "Legal review of PED 2014/68/EU applicability, document derogation rationale",
             "MONITOR", "Quality"),
    RiskItem("RISK-010", "Operational", "Beam Downtime from Valve Failure",
             "Each QPLANT trip causes proton beam downtime. Estimated 12h MDT per event.",
             3, 5, 15, "Redundant valve paths, hot standby valves, rapid isolation procedures",
             "MITIGATED", "Operations"),
]

OPERATIONAL_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "OPS-BASELINE",
        "name": "Baseline Operations",
        "availability_pct": 99.0,
        "operating_hours_year": 8000,
        "mdt_hours": 12,
        "mttr_hours": 4,
        "planned_outage_days": 45,
        "beam_trips_per_year": 3,
        "he_loss_kg_year": 65,
        "description": "Standard operations with expected failure rates and maintenance schedule",
    },
    {
        "id": "OPS-EXTENDED-REPAIR",
        "name": "Extended Repair Scenario",
        "availability_pct": 98.5,
        "operating_hours_year": 8000,
        "mdt_hours": 24,
        "mttr_hours": 8,
        "planned_outage_days": 45,
        "beam_trips_per_year": 5,
        "he_loss_kg_year": 75,
        "description": "Supply chain delays extend MTTR from 4h to 8h",
    },
    {
        "id": "OPS-CASCADE",
        "name": "Multiple/Cascade Failure",
        "availability_pct": 97.0,
        "operating_hours_year": 8000,
        "mdt_hours": 48,
        "mttr_hours": 12,
        "planned_outage_days": 60,
        "beam_trips_per_year": 8,
        "he_loss_kg_year": 120,
        "description": "One leak → increased load → more leaks cascade scenario",
    },
    {
        "id": "OPS-LOOP",
        "name": "LOOP Event (Loss of Instrument Air)",
        "availability_pct": 95.0,
        "operating_hours_year": 8000,
        "mdt_hours": 72,
        "mttr_hours": 24,
        "planned_outage_days": 45,
        "beam_trips_per_year": 1,
        "he_loss_kg_year": 200,
        "description": "Loss of instrument air, all pneumatic valves fail, He recovery triggered",
    },
]

def risk_matrix_data() -> List[Dict[str, Any]]:
    """Return risk register as list of dicts for visualization."""
    return [
        {
            "id": r.id, "category": r.category, "title": r.title,
            "description": r.description, "likelihood": r.likelihood,
            "impact": r.impact, "risk_score": r.risk_score,
            "mitigation": r.mitigation, "status": r.status, "owner": r.owner,
        }
        for r in RISK_REGISTER
    ]

def beam_impact_analysis() -> Dict[str, Any]:
    """Calculate beam availability impact from valve failures."""
    beam_hours_year = 8000
    experiments_per_hour = 0.5  # simplified
    
    scenarios = {}
    for ops in OPERATIONAL_SCENARIOS:
        lost_hours = ops["beam_trips_per_year"] * ops["mdt_hours"]
        lost_experiments = lost_hours * experiments_per_hour
        cost_per_lost_hour = 15000  # estimated €/hour of beam time
        financial_impact = lost_hours * cost_per_lost_hour
        
        scenarios[ops["id"]] = {
            "name": ops["name"],
            "beam_trips": ops["beam_trips_per_year"],
            "mdt_hours": ops["mdt_hours"],
            "lost_beam_hours": lost_hours,
            "lost_experiments": lost_experiments,
            "financial_impact_eur": financial_impact,
            "availability_pct": ops["availability_pct"],
        }
    
    return scenarios

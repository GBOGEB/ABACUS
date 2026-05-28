# Chapter 1: Introduction & QPLANT Cryogenic System Overview

## 1.1 What is ABACUS?

ABACUS (Automated Build And Continuous Unified System) is a recursive, self-improving multi-agent 
system that applies the DMAIC (Define, Measure, Analyze, Improve, Control) methodology to 
cryogenic engineering analysis, specifically for the QPLANT cryoplant system at SCK•CEN.

## 1.2 The QPLANT Context

QPLANT is a cryogenic plant system requiring rigorous engineering analysis. ABACUS provides:
- **Automated requirement traceability** via RTM (Requirements Traceability Matrix)
- **Statistical process control** for cryo system parameters
- **Anomaly detection** for thermal and pressure data
- **Continuous improvement** through recursive DMAIC cycles

### QPLANT RTM
The `QPLANT_RTM.xlsx` contains 16 formal requirements tracked across the DMAIC lifecycle:
- Located at: `rtm_integration/automation/docs/rtm/QPLANT_RTM.xlsx`
- Engineering handover: `rtm_integration/docs/QPLANT_RTM_Engineering_Handover.md`
- Analysis summary: `rtm_integration/docs/QPLANT_RTM_Analysis_Summary.md`

## 1.3 System Goals
1. **Automated Analysis** — Apply DMAIC phases automatically to cryo engineering data
2. **Self-Improvement** — Each cycle improves upon the previous through convergence detection
3. **Knowledge Preservation** — DOW governance ensures no knowledge loss between versions
4. **Traceability** — Complete audit trail from requirement to implementation

## 1.4 Key Metrics
| Metric | Value |
|--------|-------|
| Git Commits | 558 |
| Python Files | 201 |
| Documentation Files | 533 |
| DOW References | 1,327 |
| Active Versions | 5 (v2.1, v0.31, v0.32, v2.3, v3.3) |
| DMAIC Phases | 10 (0-9) |
| Agent Types | 6 |
| Orchestrator Levels | 4 |
| Quality Score | 92.5/100 |

## 1.5 Document Conventions
- 🟢 = Working/Implemented
- 🟡 = Partial/In Progress  
- 🔴 = Broken/Blocked
- ⚠️ = Requires Attention
- > *Reconstructed from code* = Content inferred from analysis

# Chapter 3: Clusters 1-4 — Analysis Layer

## 3.1 Overview
The Analysis Layer implements the core DMAIC methodology phases: Define, Measure, Analyze, Improve.

## 3.2 Cluster 1 (C1): Define Agent — Baseline

**Purpose:** Problem scoping, requirements gathering, file scanning & categorization

**Implementation:** `DMAIC_V3/phases/phase1_define.py`

**Capabilities:**
- Workspace scanning (130k+ files in full scope)
- File categorization by type, purpose, and version
- Requirement extraction from RTM artifacts
- Scope definition for improvement targets

**DMAIC Mapping:** Phase 1 (Define)

## 3.3 Cluster 2 (C2): Measure Agent — Anomaly Detection

**Purpose:** Data collection, baseline measurement, static analysis

**Implementation:** `DMAIC_V3/phases/phase2_measure.py`

**Capabilities:**
- Chunked processing (5000 files per chunk for scalability)
- Static code analysis metrics
- Baseline measurement establishment
- Anomaly detection in measurement data

**DMAIC Mapping:** Phase 2 (Measure)

## 3.4 Cluster 3 (C3): Analyze Agent — Pattern Detection

**Purpose:** Root cause analysis, pattern detection across codebase

**Implementation:** `DMAIC_V3/phases/phase3_analyze.py`

**Capabilities:**
- Root cause identification
- Pattern detection across versions
- Cross-reference analysis
- Dependency mapping

**DMAIC Mapping:** Phase 3 (Analyze)

## 3.5 Cluster 4 (C4): Improve Agent — Intervention

**Purpose:** Solution generation, code modification, optimization

**Implementation:** `DMAIC_V3/phases/phase4_improve.py`

**Capabilities:**
- Real code modifications (100 files per iteration)
- Improvement plan generation
- Optimization suggestions
- Refactoring execution

**DMAIC Mapping:** Phase 4 (Improve)

## 3.6 Data Flow
```
C1 (Define) → scope & requirements
    ↓
C2 (Measure) → baseline data
    ↓
C3 (Analyze) → root causes & patterns
    ↓
C4 (Improve) → modifications & solutions
    ↓
→ Control Layer (C7-C8)
```

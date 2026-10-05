from DMAIC_V3.agents.self_improvement_agent import SelfImprovementAgent


def _agent():
    return object.__new__(SelfImprovementAgent)


def test_root_causes_generate_control_and_optimize_improvements():
    agent = _agent()
    opportunities = [
        {
            "type": "missing_output",
            "phase": 4,
            "priority": "HIGH",
            "description": "missing",
        },
        {
            "type": "small_output",
            "file": "tiny.json",
            "size": 12,
            "priority": "MEDIUM",
            "description": "small",
        },
        {
            "type": "agent_underutilization",
            "current_agents": 3,
            "expected_agents": 12,
            "priority": "HIGH",
            "description": "agents",
        },
    ]

    roots = agent._analyze_root_causes(opportunities, {})
    improvements = agent._generate_improvements(roots)
    validated = agent._control_improvements(improvements)
    optimized = agent._optimize_improvements(validated)

    assert [item["impact"] for item in roots] == ["HIGH", "MEDIUM", "HIGH"]
    assert [item["type"] for item in improvements] == [
        "fix_phase_execution",
        "enhance_data_processing",
        "fix_agent_initialization",
    ]
    assert len(validated) == 3
    assert all(item["validated"] is True for item in validated)
    assert all(item["validation_notes"] == ["All checks passed"] for item in validated)
    assert all("implementation" in item for item in optimized)
    assert optimized[0]["implementation"]["estimated_duration"] == "4-8 hours"
    assert "Phase execution framework" in optimized[0]["implementation"]["dependencies"]
    assert "Agent manager" in optimized[2]["implementation"]["dependencies"]


def test_control_rejects_invalid_improvement_and_records_reasons():
    agent = _agent()
    invalid = {
        "id": "IMP-X",
        "type": "custom",
        "target": "Thing",
        "action": "Do work",
        "expected_outcome": "Better",
        "priority": "URGENT",
        "effort": "UNKNOWN",
    }

    validated = agent._control_improvements([invalid])

    assert validated == []
    assert invalid["validated"] is False
    assert "Invalid priority level" in invalid["validation_notes"]
    assert "Invalid effort level" in invalid["validation_notes"]


def test_helper_defaults_effort_and_success_metrics():
    agent = _agent()
    unknown = {
        "type": "other",
        "target": "misc",
        "expected_outcome": "Works",
        "effort": "UNKNOWN",
        "priority": "LOW",
    }
    optimized = [
        {"priority": "HIGH", "effort": "HIGH"},
        {"priority": "MEDIUM", "effort": "MEDIUM"},
        {"priority": "LOW", "effort": "LOW"},
    ]

    assert agent._generate_implementation_steps(unknown) == [
        "1. Analyze issue",
        "2. Implement fix",
        "3. Test",
        "4. Validate",
    ]
    assert agent._estimate_duration(unknown) == "Unknown"
    assert agent._identify_dependencies(unknown) == ["None"]
    assert agent._define_success_criteria(unknown)[0] == "Works"
    assert agent._calculate_total_effort(optimized) == "2.4 days"

    metrics = agent._measure_success({"baseline": 1}, optimized)
    assert metrics["improvements_count"] == 3
    assert metrics["high_priority_count"] == 1
    assert metrics["medium_priority_count"] == 1
    assert metrics["low_priority_count"] == 1
    assert metrics["success_rate"] == 100.0

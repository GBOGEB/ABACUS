from tools.generic_3p_selector import select_method


def test_evidence_uncertainty_selects_3pe():
    result = select_method({"state": "S0_UNKNOWN", "semantic_weights": {"E": 0.9}})
    assert result["chain"] == ["3PE"]


def test_search_pressure_can_insert_3pl():
    result = select_method({
        "state": "S1_DISCOVERED",
        "semantic_weights": {"E": 0.7, "L": 0.2},
        "aht_pressure": 0.9,
        "low_yield_pressure": 0.9,
    })
    assert result["chain"][:2] == ["3PE", "3PL"]


def test_authority_and_information_loss_select_3pc_then_3pv():
    result = select_method({
        "state": "S2_CLASSIFIED",
        "semantic_weights": {"C": 0.8, "I": 0.9},
    })
    assert result["chain"] == ["3PC", "3PV"]


def test_reentry_appends_3pr():
    result = select_method({
        "state": "S4_REINTRODUCED",
        "semantic_weights": {"V": 0.8, "R": True},
    })
    assert result["chain"][-1] == "3PR"


def test_terminal_closed_item_stops():
    result = select_method({
        "state": "S6_TERMINAL",
        "semantic_weights": {},
        "dov_gap": 0.0,
    })
    assert result["decision"] == "STOP"
    assert result["chain"] == []


def test_rework_pressure_forces_proof():
    result = select_method({
        "state": "S2_CLASSIFIED",
        "semantic_weights": {},
        "rework_pressure": 0.8,
    })
    assert "3PV" in result["chain"]

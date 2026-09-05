from qplant.w52_p2l_b_flow_enthalpy import topology_receipt


def test_topology_implies_40_68_g_s_B_return():
    r = topology_receipt()
    assert abs(r.B_implied_g_s - 40.68) < 1e-12
    assert abs(r.mass_checksum_g_s) < 1e-12
    assert r.strict_residual_status == "CHECKSUM_ONLY_NOT_INDEPENDENT_PASS"


def test_B_is_not_promoted_to_independent_evidence():
    r = topology_receipt()
    assert r.evidence_class == "DERIVED_FROM_SOURCE_BOUND_TOPOLOGY"

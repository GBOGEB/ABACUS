from qplant.w52_p2h_wcs_thermo_proof import nominal_2kop_configurations


def test_nominal_326_g_s_supports_both_hp_configurations():
    cfg = nominal_2kop_configurations(326.0)
    assert cfg[0]["active_units"] == 3
    assert abs(cfg[0]["flow_per_active_unit_g_s"] - 108.6666666667) < 1e-9
    assert cfg[1]["active_units"] == 4
    assert cfg[1]["flow_per_active_unit_g_s"] == 81.5
    assert all(row["status"] == "CANDIDATE_NOT_SELECTED" for row in cfg)

from tools.w64_3p_anchor_watch import metric_status, pca_status


def test_metric_controlled_anchor_stays_controlled():
    r = metric_status(101.0, 100.0, 2.0, [0.2, -0.1])
    assert r["status"] == "CONTROLLED"
    assert r["reopen_analyze"] is False


def test_single_warning_does_not_reopen():
    r = metric_status(104.5, 100.0, 2.0, [])
    assert r["status"] == "WARNING"
    assert r["reopen_analyze"] is False


def test_repeated_breaches_reopen_measure_analyze():
    r = metric_status(107.0, 100.0, 2.0, [3.2])
    assert r["status"] == "DRIFT"
    assert r["reopen_analyze"] is True


def test_six_sigma_event_reopens_immediately():
    r = metric_status(112.0, 100.0, 2.0, [])
    assert r["status"] == "DRIFT"
    assert r["reopen_analyze"] is True


def test_pca_sign_flip_is_still_same_component():
    anchor = {"loadings": [0.6, 0.5, 0.4], "explained_variance": 0.48, "semantic_label": "authority_risk"}
    current = {"loadings": [-0.61, -0.49, -0.39], "explained_variance": 0.47, "semantic_label": "authority_risk"}
    r = pca_status(current, anchor)
    assert r["status"] == "CONTROLLED"
    assert r["cosine_similarity"] > 0.99


def test_pca_repeated_breach_reopens():
    anchor = {"loadings": [0.8, 0.1, 0.1], "explained_variance": 0.50, "semantic_label": "authority_risk"}
    current = {"loadings": [0.1, 0.8, 0.1], "explained_variance": 0.35, "semantic_label": "authority_risk"}
    r = pca_status(current, anchor, ["BREACH"])
    assert r["status"] == "DRIFT"
    assert r["reopen_analyze"] is True

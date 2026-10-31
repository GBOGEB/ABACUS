from abacus_runtime.w98_qps_glossary_projection import contractor_safe, project

ROWS = [
    {
        "token": "QPS",
        "authority": "SCK_CEN_CONTRACTUAL",
        "scope": "QPS",
        "source_exactness": "SOURCE_EXACT",
        "collision_type": "SCOPE_DELTA",
        "disposition": "FLAG_CONFLICT",
    },
    {
        "token": "QPS",
        "authority": "SUPPLIER_A_APPLICANT",
        "scope": "QPS",
        "source_exactness": "SOURCE_EXACT",
        "collision_type": "SCOPE_DELTA",
        "disposition": "FLAG_CONFLICT",
    },
    {
        "token": "MTBF",
        "authority": "SUPPLIER_B_APPLICANT",
        "scope": "PROJECT_WIDE",
        "source_exactness": "SOURCE_EXACT",
        "collision_type": "DEFINITION_DELTA",
        "disposition": "ACCEPT_CANONICAL",
    },
    {
        "token": "PLOC",
        "authority": "GENERAL_RELATED",
        "scope": "QPLANT",
        "source_exactness": "SOURCE_EXACT",
        "collision_type": "NONE",
        "disposition": "ALIAS_ONLY",
    },
]


def test_projection_is_deterministic():
    assert (
        project(ROWS)["deterministic_projection_digest"]
        == project(list(reversed(ROWS)))["deterministic_projection_digest"]
    )


def test_supplier_a_view_excludes_supplier_b():
    view = contractor_safe(ROWS, "SUPPLIER_A")
    assert not any(r["authority"] == "SUPPLIER_B_APPLICANT" for r in view)


def test_supplier_b_view_excludes_supplier_a():
    view = contractor_safe(ROWS, "SUPPLIER_B")
    assert not any(r["authority"] == "SUPPLIER_A_APPLICANT" for r in view)


def test_metrics_keep_zero_credit():
    metrics = project(ROWS)
    assert metrics["total_terms"] == 4
    assert metrics["conflict_count"] == 3
    assert metrics["credit_delta"] == 0

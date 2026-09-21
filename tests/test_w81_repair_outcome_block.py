from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

w81=load_module("w81",ROOT/"tools/w81_repair_outcome_block.py")

def test_w81_contract_is_fail_closed_and_non_promotional():
    c=json.loads((ROOT/"architecture/w81/W81_REPAIR_OUTCOME_CONTRACT.json").read_text())
    assert c["source_w80"]["pc1_predictive_validation"] is False
    assert c["source_w80"]["pairwise_outcome_accumulation_permitted"] is False
    assert c["promotion_guards"]["current_bt_eligibility"] is False
    assert len(c["episodes"]) == 2
    assert c["excluded_episode"]["name"] == "W79_1204_TO_1206"
    assert "NOT_RED_TO_GREEN" in c["excluded_episode"]["reason"]

def test_pair_graph_is_disconnected_for_two_independent_episodes():
    events=[
        {"winner_source_sha":"a","loser_source_sha":"b"},
        {"winner_source_sha":"c","loser_source_sha":"d"},
    ]
    assert w81.components(events) == 2

"""Negative and positive tests for read-only async/cache runtime contracts."""
import asyncio
import math
from pathlib import Path
import pytest
from scripts import cbd_eoss_runtime_probe as runtime

DIGEST="a"*64


def sample_wheel():
    return dict(python_abi="cp312",runner_os="ubuntu-24.04",runner_arch="x86_64",
                lock_sha256=DIGEST,index_identity="approved-index-v1",
                wheels={"CoolProp-7.1.0-cp312-cp312-manylinux.whl":DIGEST})


def test_cache_key_reproducible_but_not_performance_claim():
    a=runtime.wheelhouse_key(**sample_wheel())
    b=runtime.wheelhouse_key(**sample_wheel())
    assert a==b
    assert len(a["key_sha256"])==64
    assert a["time_saved_seconds"] is None
    assert a["wheels_verified_by_caller"] is False
    assert a["preload_installed"] is False


def test_cache_key_changes_with_abi_or_lock():
    before=runtime.wheelhouse_key(**sample_wheel())["key_sha256"]
    args=sample_wheel();args["python_abi"]="cp313"
    assert runtime.wheelhouse_key(**args)["key_sha256"] != before
    args=sample_wheel();args["lock_sha256"]="b"*64
    assert runtime.wheelhouse_key(**args)["key_sha256"] != before


@pytest.mark.parametrize("change",[
    {"python_abi":""},{"runner_arch":None},{"index_identity":" "},
    {"lock_sha256":"unverified"},{"wheels":{}},
    {"wheels":{"../../escape.whl":DIGEST}},
    {"wheels":{"package.whl":"bad"}},
])
def test_bad_cache_inputs_fail_closed(change):
    args=sample_wheel();args.update(change)
    with pytest.raises(ValueError):runtime.wheelhouse_key(**args)


def sample_pairs():
    return [{"trial_id":str(i),"cohort_sha256":DIGEST,
             "cold_elapsed_seconds":300+i,"warm_elapsed_seconds":25+i}
            for i in range(3)]


def test_three_matched_pairs_report_local_paired_median_only():
    result=runtime.paired_cache_result(sample_pairs())
    assert result["median_paired_saved_seconds"]==275
    assert result["trial_count"]==3
    assert result["github_runner_cache_savings_certified"] is False
    assert result["merge_authorized"] is False


def test_nonimproving_pair_is_not_greenwashed():
    pairs=sample_pairs();pairs[1]["warm_elapsed_seconds"]=500
    report=runtime.paired_cache_result(pairs)
    assert report["all_pairs_improved"] is False
    assert report["median_paired_saved_seconds"]==275


@pytest.mark.parametrize("change",[
    lambda x:x.pop(),
    lambda x:x[1].update(trial_id="0"),
    lambda x:x[1].update(cohort_sha256="b"*64),
    lambda x:x[1].update(warm_elapsed_seconds=None),
    lambda x:x[0].update(cold_elapsed_seconds=True),
    lambda x:x[0].update(warm_elapsed_seconds=math.inf),
])
def test_unqualified_cache_pairs_rejected(change):
    rows=sample_pairs();change(rows)
    with pytest.raises(ValueError):runtime.paired_cache_result(rows)


def run(coro):
    return asyncio.run(coro)


def test_async_readonly_scout_is_bounded_with_eight_tasks():
    async def fetch(rid):
        await asyncio.sleep(.002)
        return {"run_id":rid}
    result=run(runtime.scout_read_only(list(range(1,9)),fetch,limit=4))
    assert result["bound"]==8 and result["withheld"]==0
    assert 1 < result["maximum_concurrent_observed"] <= 4
    assert result["authenticated_crew_dispatch"] is False
    assert result["native_runner_queue_wait"] is None


def test_async_failed_callback_withheld_not_counted_green():
    async def fetch(rid):
        if rid==2:raise RuntimeError("simulated API failure")
        if rid==3:return {"run_id":99}
        return {"run_id":rid}
    result=run(runtime.scout_read_only([1,2,3],fetch))
    assert result["bound"]==1 and result["withheld"]==2
    assert [row["status"] for row in result["observations"]]==[
        "BOUND_METADATA","READBACK_WITHHELD","READBACK_WITHHELD"]


def test_async_timeout_is_explicitly_censored():
    async def slow(_):
        await asyncio.sleep(.02)
        return {"run_id":1}
    result=run(runtime.scout_read_only([1],slow,timeout_seconds=.001))
    assert result["withheld"]==1 and result["bound"]==0


@pytest.mark.parametrize("ids,limit,timeout",[
    ([],4,2),([1,1],4,2),([True],4,2),([1],5,2),
    ([1],0,2),([1],True,2),([1],4,0),([1],4,121),
])
def test_readonly_boundaries_reject_bad_scout_request(ids,limit,timeout):
    async def fetch(rid): return {"run_id":rid}
    with pytest.raises(ValueError):run(runtime.scout_read_only(ids,fetch,limit=limit,timeout_seconds=timeout))

"""MACH-II red canary (PR #2470): fails on purpose. Never merge."""


def test_mach_ii_red_canary_must_block_merge():
    assert False, "MACH-II canary: required status checks must keep this PR BLOCKED"

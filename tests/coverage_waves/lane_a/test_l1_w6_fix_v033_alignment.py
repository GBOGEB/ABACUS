"""Behaviour tests for ABACUS-v032/fix_v033_alignment.py.

The module rewrites a file next to its own ``__file__``; every test points
``__file__`` at ``tmp_path`` so the repository is never touched. The module
does not call subprocess, but it is stubbed anyway so nothing external runs.
"""

import pytest

from tests.coverage_waves.lane_a._load import load

fix = load("ABACUS-v032/fix_v033_alignment.py")

TARGET = "execute_full_dmaic_phases_0_to_9_v033.py"


@pytest.fixture
def ws(monkeypatch, tmp_path):
    def _no_subprocess(*args, **kwargs):
        raise AssertionError("subprocess must not be called")

    monkeypatch.setattr("subprocess.run", _no_subprocess)
    monkeypatch.setattr("subprocess.check_output", _no_subprocess)
    monkeypatch.setattr(fix, "__file__", str(tmp_path / "fix_v033_alignment.py"))
    return tmp_path


def _write(ws, text):
    (ws / TARGET).write_bytes(text.encode("utf-8"))


def _read(ws):
    # write_text emits CRLF on Windows; compare with LF line endings
    return (ws / TARGET).read_bytes().decode("utf-8").replace("\r\n", "\n")


def test_missing_target_raises(ws):
    with pytest.raises(FileNotFoundError):
        fix.clean_and_update_v033()


def test_replaces_header_up_to_orchestrator_class(ws, capsys):
    src = "\n".join(
        [
            "#!/usr/bin/env python3",
            '"""old docstring"""',
            "import os",
            "",
            "class FullDMAICOrchestrator:",
            "    def run(self):",
            "        return 42",
        ]
    )
    _write(ws, src)
    fix.clean_and_update_v033()
    out = _read(ws)
    assert out.startswith("#!/usr/bin/env python3\n# -*- coding: utf-8 -*-")
    assert "SPRINT TESTED | DOW TESTED | CANONICAL ALIGNED" in out
    assert "Version History:" in out
    assert "sprint_tested: bool = False" in out
    assert "dow_tested: bool = False" in out
    assert "self.canonical_aligned = True" in out
    assert "old docstring" not in out
    assert out.count("class FullDMAICOrchestrator:") == 1
    assert out.endswith("    def run(self):\n        return 42")
    printed = capsys.readouterr().out
    assert "Reading" in printed
    assert "Writing cleaned content" in printed
    assert "File cleaned and updated successfully" in printed


def test_conflict_markers_removed_and_duplicate_shebang_dropped(ws):
    src = "\n".join(
        [
            "<<<<<<< HEAD",
            "#!/usr/bin/env python3",
            "=======",
            "#!/usr/bin/env python3",
            ">>>>>>> branch",
            "",
            "x = 1",
            "",
            "class FullDMAICOrchestrator:",
            "    pass",
        ]
    )
    _write(ws, src)
    fix.clean_and_update_v033()
    out = _read(ws)
    assert "<<<<<<<" not in out
    assert ">>>>>>>" not in out
    assert "\n=======\n" not in out
    # the duplicated shebang collapsed before the header regex replaced it
    assert out.count("#!/usr/bin/env python3") == 1
    # everything from the shebang through the class line is the new header
    assert "x = 1" not in out
    assert out.endswith("self.canonical_aligned = True\n\n    pass")


def test_blank_lines_after_conflict_dropped_only_in_first_70_lines(ws):
    lines = ["# body", "<<<<<<< ours", "a = 1", "", "b = 2"]
    lines.extend("# filler {}".format(n) for n in range(70))
    lines.extend(["", "tail = 3"])
    _write(ws, "\n".join(lines))
    fix.clean_and_update_v033()
    out = _read(ws)
    # no shebang/class pair, so no header replacement happens
    assert "SPRINT TESTED" not in out
    assert "a = 1\nb = 2" in out
    # blank line beyond index 70 is kept even though in_conflict is still True
    assert "\n\ntail = 3" in out


def test_blank_lines_kept_without_conflict(ws):
    _write(ws, "a = 1\n\nb = 2")
    fix.clean_and_update_v033()
    assert _read(ws) == "a = 1\n\nb = 2"


def test_second_shebang_without_preceding_shebang_is_kept(ws):
    _write(ws, "x = 0\n#!/usr/bin/env python3\ny = 1")
    fix.clean_and_update_v033()
    assert _read(ws) == "x = 0\n#!/usr/bin/env python3\ny = 1"

"""Root refactor tools end to end: apply, check, inventory and the map CLI in a scratch git repo."""

from __future__ import annotations

import contextlib
import csv
import importlib.util
import inspect
import io
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools" / "root_refactor"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


relocate = load("root_relocate_e2e", "relocate.py")
inventory = load("root_inventory_e2e", "inventory.py")
page_mod = load("root_discovery_page_e2e", "discovery_page.py")

FILES = {
    "README.md": "# Repo\n\nSee [report](Report_20240101_120000.md).\n",
    "Report_20240101_120000.md": "# Run\n\nBack to [readme](README.md).\n",
    "SESSION_HANDOVER.md": "# Handover\n",
    "STATUS_SUMMARY.md": "",
    "GUIDE.md": "# Guide\n",
    "COPY_OF_GUIDE.md": "# Guide\n",
    "tool.py": "print('hi')\n",
    "docs/notes.md": "Uses [the guide](../GUIDE.md).\n",
    "scripts/run.sh": "cat docs/STATUS_SUMMARY.md\n",
}
MAP_ROWS = [
    [
        "Report_20240101_120000.md",
        "docs_versioned/generated_reports/Report_20240101_120000.md",
        "F1",
        "W1",
        "ARCHIVE_PRESERVE_LINKS",
    ],
    [
        "GUIDE.md",
        "docs_versioned/guides/GUIDE.md",
        "F4",
        "W4",
        "MOVE_WITH_CONSUMER_REPLAY",
    ],
]


def run_quiet(fn, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = fn(*args)
    return code, out.getvalue(), err.getvalue()


class ScratchRepo(unittest.TestCase):
    def setUp(self):
        # Plain mkdir, not tempfile.mkdtemp: its owner-only ACL on Windows
        # (Python 3.12.4+) keeps git from entering the folder.
        self.root = (
            Path(tempfile.gettempdir()) / f"root-refactor-e2e-{uuid.uuid4().hex}"
        )
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        # The folder may be owned by Administrators while tests run as the user;
        # GIT_CONFIG_* counts as command-line config, where safe.directory applies.
        env = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": "*",
        }
        patchers = [mock.patch.dict(os.environ, env)]
        for module in (relocate, inventory, page_mod, page_mod.relocate_mod):
            real_root = module.ROOT
            patchers.append(mock.patch.object(module, "ROOT", self.root))
            # `root: Path = ROOT` defaults were bound at import time
            for fn in vars(module).values():
                if (
                    inspect.isfunction(fn)
                    and fn.__defaults__
                    and real_root in fn.__defaults__
                ):
                    defaults = tuple(
                        self.root if d == real_root else d for d in fn.__defaults__
                    )
                    patchers.append(mock.patch.object(fn, "__defaults__", defaults))
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        for rel, text in FILES.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        self.write_map(MAP_ROWS)
        relocate.git("init", "-q")
        self.commit("seed")

    def write_map(self, rows, header=relocate.FIELDS):
        path = self.root / relocate.MAP
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)

    def commit(self, message):
        relocate.git("add", "-A")
        relocate.git(
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            message,
        )


class RelocateEndToEndTest(ScratchRepo):
    def test_check_reports_every_unapplied_move(self):
        errors = relocate.check(self.root)
        self.assertIn(
            "Report_20240101_120000.md: still at repo root (wave W1 not applied or file re-added)",
            errors,
        )
        self.assertIn(
            "docs_versioned/guides/GUIDE.md: relocation target missing", errors
        )
        self.assertIn(
            "README.md: link still points at moved root file Report_20240101_120000.md",
            errors,
        )
        self.assertIn(
            "docs/notes.md: link still points at moved root file GUIDE.md", errors
        )

    def test_apply_moves_rewrites_and_is_idempotent(self):
        code, out, _ = run_quiet(relocate.main, ["apply", "--wave", "W1"])
        self.assertEqual(code, 0)
        self.assertIn("W1: moved 1 file(s); rewrote links in 2 document(s)", out)
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "(docs_versioned/generated_reports/Report_20240101_120000.md)", readme
        )
        moved = self.root / "docs_versioned/generated_reports/Report_20240101_120000.md"
        self.assertIn("(../../README.md)", moved.read_text(encoding="utf-8"))
        self.assertEqual(
            run_quiet(relocate.main, ["apply", "--wave", "W1"])[1],
            "W1: nothing to move (already applied or no rows)\n",
        )

    def test_check_cli_passes_once_every_wave_is_applied(self):
        run_quiet(relocate.main, ["apply", "--wave", "W1"])
        run_quiet(relocate.main, ["apply", "--wave", "W4"])
        code, out, err = run_quiet(relocate.main, ["check"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("2 mapped file(s), 0 problem(s)", out)

    def test_check_cli_fails_on_a_code_consumer(self):
        self.write_map(
            MAP_ROWS
            + [["tool.py", "tools/tool.py", "F5", "W5", "MOVE_WITH_CONSUMER_REPLAY"]]
        )
        (self.root / "Makefile").write_text(
            "run:\n\tpython tool.py\n", encoding="utf-8"
        )
        relocate.git("add", "-A")
        for wave in ("W1", "W4", "W5"):
            run_quiet(relocate.main, ["apply", "--wave", wave])
        code, _, err = run_quiet(relocate.main, ["check"])
        self.assertEqual(code, 1)
        self.assertIn(
            "Makefile: code or config still names moved root file tool.py", err
        )

    def test_invalid_map_blocks_apply_and_check(self):
        self.write_map([["a.md", "b.md", "F9", "Wx", "DELETE"]])
        code, _, err = run_quiet(relocate.main, ["apply", "--wave", "W1"])
        self.assertEqual(code, 1)
        self.assertIn("family 'F9'", err)
        self.assertIn("must be a repo-relative sub-folder path", err)
        self.write_map([["a.md", "x/a.md"]], header=["old_path", "new_path"])
        self.assertEqual(
            relocate.check(self.root),
            [f"{relocate.MAP}: header must be {','.join(relocate.FIELDS)}"],
        )

    def test_missing_map_means_nothing_mapped(self):
        (self.root / relocate.MAP).unlink()
        self.assertEqual(relocate.load_map(self.root), [])
        self.assertEqual(relocate.check(self.root), [])


class InventoryEndToEndTest(ScratchRepo):
    def test_rows_classify_count_refs_and_flag_prune_candidates(self):
        rows = {r["path"]: r for r in inventory.inventory()}
        self.assertEqual(set(rows), {p for p in FILES if "/" not in p})
        self.assertEqual(rows["README.md"]["family"], "KEEP")
        self.assertEqual(
            (
                rows["Report_20240101_120000.md"]["family"],
                rows["Report_20240101_120000.md"]["wave"],
            ),
            ("F1", "W1"),
        )
        self.assertEqual(rows["SESSION_HANDOVER.md"]["family"], "F2")
        self.assertEqual(rows["STATUS_SUMMARY.md"]["prune_candidate"], "empty-file")
        self.assertEqual(
            rows["COPY_OF_GUIDE.md"]["prune_candidate"], "exact-dup-of:GUIDE.md"
        )
        self.assertEqual(rows["tool.py"]["family"], "F5")
        self.assertEqual(
            rows["STATUS_SUMMARY.md"]["hard_ref_files"], 1
        )  # scripts/run.sh
        self.assertGreaterEqual(rows["GUIDE.md"]["inbound_files"], 1)
        self.assertEqual(inventory.classify("notes.txt"), ("UNCLASSIFIED", ""))

    def test_write_cli_emits_the_csv_and_fails_on_unclassified(self):
        code, out, _ = run_quiet(inventory.main, ["--write"])
        self.assertEqual(code, 0)
        self.assertIn(f"wrote {inventory.OUT}", out)
        self.assertIn("F1", out)
        with (self.root / inventory.OUT).open(encoding="utf-8") as f:
            self.assertEqual(next(csv.reader(f)), inventory.FIELDS)
        (self.root / "notes.txt").write_text("x\n", encoding="utf-8")
        self.commit("unclassified")
        self.assertEqual(run_quiet(inventory.main, [])[0], 1)


class DiscoveryPageCliTest(ScratchRepo):
    def setUp(self):
        super().setUp()
        run_quiet(inventory.main, ["--write"])

    def test_write_then_check_then_stale(self):
        code, out, _ = run_quiet(page_mod.main, ["--write"])
        self.assertEqual(code, 0)
        self.assertIn(f"wrote {page_mod.OUT}", out)
        self.assertEqual(
            run_quiet(page_mod.main, ["--check"])[:2],
            (0, f"{page_mod.OUT} is up to date\n"),
        )
        (self.root / page_mod.OUT).write_text("old\n", encoding="utf-8")
        code, _, err = run_quiet(page_mod.main, ["--check"])
        self.assertEqual(code, 1)
        self.assertIn("is stale", err)

    def test_summary_counts_inventory_and_moves(self):
        code, out, _ = run_quiet(page_mod.main, [])
        self.assertEqual(code, 0)
        self.assertIn(f"{len(FILES) - 2} root files at inventory, 2 moved", out)


if __name__ == "__main__":
    unittest.main()

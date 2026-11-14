"""The gg_MATH bridge loads only the pinned kernel bytes, and fails closed on anything else."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import unittest
import unittest.mock as mock

from tests.binary_engines import _env

KERNEL = b'"""A stand-in kernel."""\nVALUE = 42\n\n\ndef twice(x):\n    return 2 * x\n'


def _pin(data: bytes, bridge) -> dict:
    return {
        "commit": "f" * 40,
        "path": "kernels/stand_in.py",
        "blob": bridge.blob_id(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


class Pins(unittest.TestCase):
    def setUp(self):
        _env.require("yaml")
        self.bridge = _env.engine("ggmath_bridge")

    def test_pins_are_exact(self):
        for name, pin in self.bridge.PINS.items():
            with self.subTest(kernel=name):
                self.assertRegex(pin["commit"], r"^[0-9a-f]{40}$")
                self.assertRegex(pin["blob"], r"^[0-9a-f]{40}$")
                self.assertRegex(pin["sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(pin["path"], f"kernels/{name}.py")

    def test_workflow_checks_out_the_pinned_commit(self):
        workflow = (
            _env.REPO / ".github" / "workflows" / "binary-engines.yml"
        ).read_text("utf-8")
        refs = set(re.findall(r"GG_MATH_COMMIT:\s*([0-9a-f]{40})", workflow))
        self.assertEqual(refs, {pin["commit"] for pin in self.bridge.PINS.values()})

    def test_blob_id_is_git_object_id(self):
        # git hash-object of an empty file and of "hello\n" (well-known values)
        self.assertEqual(
            self.bridge.blob_id(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
        )
        self.assertEqual(
            self.bridge.blob_id(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a"
        )


class Loading(unittest.TestCase):
    def setUp(self):
        _env.require("yaml")
        self.bridge = _env.engine("ggmath_bridge")
        self.work = _env.HOME / "bridge_test"
        shutil.rmtree(self.work, ignore_errors=True)
        (self.work / "checkout" / "kernels").mkdir(parents=True)
        (self.work / "checkout" / "kernels" / "stand_in.py").write_bytes(KERNEL)
        patches = [
            mock.patch.dict(self.bridge.PINS, {"stand_in": _pin(KERNEL, self.bridge)}),
            mock.patch.object(self.bridge, "CACHE", self.work / "cache"),
            mock.patch.dict(os.environ, {"GG_MATH_HOME": str(self.work / "checkout")}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.bridge._LOADED.pop, "stand_in", None)
        self.addCleanup(sys.modules.pop, "ggmath_stand_in", None)

    def test_loads_pinned_bytes_and_caches_them(self):
        module = self.bridge.load("stand_in")
        self.assertEqual(module.twice(module.VALUE), 84)
        self.assertEqual(module.GG_MATH_PIN["repo"], "GBOGEB/gg_MATH")
        cached = list((self.work / "cache").iterdir())
        self.assertEqual([p.read_bytes() for p in cached], [KERNEL])
        self.assertFalse(
            any(p.name == "__pycache__" for p in (self.work / "cache").iterdir()),
            "no bytecode cache",
        )
        self.assertFalse((self.work / "checkout" / "kernels" / "__pycache__").exists())

    def test_cache_serves_without_a_checkout(self):
        self.bridge.kernel_bytes("stand_in")
        with mock.patch.dict(os.environ, {"GG_MATH_HOME": ""}):
            data, origin = self.bridge.kernel_bytes("stand_in")
        self.assertEqual(data, KERNEL)
        self.assertIn("cache", origin)

    def test_crlf_checkout_is_accepted_as_the_pinned_bytes(self):
        (self.work / "checkout" / "kernels" / "stand_in.py").write_bytes(
            KERNEL.replace(b"\n", b"\r\n")
        )
        data, _ = self.bridge.kernel_bytes("stand_in")
        self.assertEqual(data, KERNEL)

    def test_tampered_kernel_is_refused(self):
        (self.work / "checkout" / "kernels" / "stand_in.py").write_bytes(
            KERNEL.replace(b"42", b"43")
        )
        with self.assertRaisesRegex(self.bridge.KernelPinError, "blob"):
            self.bridge.load("stand_in")
        self.assertNotIn("ggmath_stand_in", sys.modules)

    def test_tampered_cache_is_not_used(self):
        self.bridge.kernel_bytes("stand_in")
        cache = next((self.work / "cache").iterdir())
        cache.write_bytes(KERNEL.replace(b"42", b"43"))
        data, origin = self.bridge.kernel_bytes(
            "stand_in"
        )  # falls back to the checkout and rewrites the cache
        self.assertEqual(data, KERNEL)
        self.assertNotIn("cache", origin)
        self.assertEqual(cache.read_bytes(), KERNEL)

    def test_no_source_fails_closed(self):
        with mock.patch.dict(os.environ, {"GG_MATH_HOME": ""}):
            with self.assertRaisesRegex(self.bridge.KernelPinError, "GG_MATH_HOME"):
                self.bridge.kernel_bytes("stand_in")
        with self.assertRaisesRegex(self.bridge.KernelPinError, "no pin"):
            self.bridge.kernel_bytes("not_a_kernel")


class RealKernels(unittest.TestCase):
    def test_pinned_kernels_load_and_compute(self):
        _env.require_kernels()
        bridge = _env.engine("ggmath_bridge")
        ss, pg = bridge.load("set_similarity"), bridge.load("plane_geometry")
        self.assertEqual(ss.jaccard({1, 2, 3}, {2, 3, 4}), 0.5)
        self.assertEqual(ss.overlap({1, 2}, {1, 2, 3}), 1.0)
        self.assertEqual(pg.box_distance((0, 0, 1, 1), 4, 5), 5.0)
        self.assertEqual(
            pg.affine_apply(pg.parse_transform("translate(2,3) scale(2)"), 1, 1),
            (4.0, 5.0),
        )


if __name__ == "__main__":
    unittest.main()

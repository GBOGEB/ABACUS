"""Reference tests of the drawing reader as unit tests: R3 adversarial (must not guess) and R4 read-only.

R3 runs the reader's own adversarial set (reference_test.r3_adversarial) case by case, plus two positive controls
that keep R3 honest: a flow marker that does give a line its direction, and an in-drawing legend that does type a
line. R4 hashes every fixture before and after all readers and probes ran. With no answer key, crosswalk or pilot
configured (the example configuration), R1, R2 and R5 must report DEFER, never PASS.
"""

from __future__ import annotations

import hashlib
import json
import unittest

from tests.binary_engines import _env, _fixtures

HEAD = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><defs><marker id="m" viewBox="0 0 10 10" '
    'refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0L10,5L0,10z"/></marker></defs>'
)
BOXES = (
    '<rect x="20" y="80" width="60" height="40" fill="#ddd" stroke="#000"/><text x="30" y="105">PUMP P-101</text>'
    '<rect x="300" y="80" width="60" height="40" fill="#ddd" stroke="#000"/><text x="310" y="105">TANK T-201</text>'
)
HOST = '<line x1="80" y1="100" x2="300" y2="100" stroke="#000"/>'


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Adversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _env.require("yaml", "lxml")
        _env.require_kernels()
        cls.rt = _env.engine("reference_test")
        cls.dg = _env.engine("deep_graph")

    def _svg(self, name, body):
        folder = _env.HOME / "fixtures" / "controls"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_text(HEAD + body + "</svg>", "utf-8")
        return self.dg.read_svg(path)

    def test_r3_adversarial_cases_refuse_to_guess(self):
        cases = self.rt.r3_adversarial()
        self.assertEqual(len(cases), 7)
        for case in cases:
            with self.subTest(case=case["case"]):
                self.assertEqual(case["result"], "PASS", case["expect"])

    def test_flow_marker_gives_the_line_its_direction(self):
        for name, marker, expected in (
            (
                "marker_forward.svg",
                '<line x1="180" y1="100" x2="190" y2="100" stroke="#000" marker-end="url(#m)"/>',
                "forward",
            ),
            (
                "marker_backward.svg",
                '<line x1="190" y1="100" x2="180" y2="100" stroke="#000" marker-end="url(#m)"/>',
                "backward",
            ),
        ):
            with self.subTest(case=name):
                g = self._svg(name, BOXES + HOST + marker)
                hosts = [e for e in g["edges"] if e["how"] == "geometric"]
                self.assertEqual(len(hosts), 1)
                self.assertEqual(hosts[0]["direction"], expected)
                self.assertEqual(hosts[0]["direction_from"], "flow_marker")
                self.assertEqual(sum(e["how"] == "flow_marker" for e in g["edges"]), 1)

    def test_in_drawing_legend_types_matching_lines(self):
        legend = (
            '<text x="200" y="20">Legend</text><line x1="200" y1="40" x2="230" y2="40" stroke="#c00"/>'
            '<text x="240" y="44">signal</text>'
        )
        g = self._svg(
            "legend_control.svg",
            BOXES + legend + '<line x1="80" y1="100" x2="300" y2="100" stroke="#c00"/>',
        )
        typed = [e for e in g["edges"] if e["how"] == "geometric"]
        self.assertEqual(len(typed), 1)
        self.assertEqual(typed[0]["semantic_type"], "signal")
        self.assertEqual(typed[0]["semantic_source"], "in_drawing_legend")

    def test_end_floating_inside_a_container_is_not_attached(self):
        # a container (25 % of the page) counts only where an end touches its border (tuning rule T2)
        frame = (
            '<rect x="100" y="30" width="200" height="100" fill="none" stroke="#000"/>'
        )
        floating = self._svg(
            "container_inside.svg",
            frame + '<line x1="150" y1="80" x2="250" y2="80" stroke="#000"/>',
        )
        self.assertEqual([e["how"] for e in floating["edges"]], ["unresolved"])
        touching = self._svg(
            "container_border.svg",
            frame + BOXES + '<line x1="80" y1="100" x2="100" y2="100" stroke="#000"/>',
        )
        attached = [e for e in touching["edges"] if e["how"] == "geometric"]
        self.assertEqual(len(attached), 1, "an end on the container border is attached")


class ReadOnly(unittest.TestCase):
    def test_r4_readers_and_probes_change_nothing(self):
        _env.require(*_env.DEPS)
        _env.require_kernels()
        spec = _env.engine("estate_spec")
        smoke = spec.ROOTS["SMOKE"][0]
        if not smoke.is_dir():
            _fixtures.build_smoke(smoke)
        rt, dg, probe = (
            _env.engine("reference_test"),
            _env.engine("deep_graph"),
            _env.engine("estate_probe"),
        )
        rt.r3_adversarial()
        files = sorted(
            p for folder in (smoke, rt.FIX) for p in folder.iterdir() if p.is_file()
        )
        before = {p: (_sha(p), p.stat().st_mtime_ns) for p in files}
        for p in files:
            ext = p.suffix.lower()
            if ext in dg.READERS:
                dg.READERS[ext](p)
            typ = spec.EXT_TO_TYPE.get(ext)
            if typ in probe.PROBES:
                probe.PROBES[typ](p)
        after = {p: (_sha(p), p.stat().st_mtime_ns) for p in files}
        self.assertGreaterEqual(len(files), 18)
        self.assertEqual(before, after)


class Unconfigured(unittest.TestCase):
    def test_r1_r2_r5_defer_without_references(self):
        _env.require("yaml", "lxml")
        _env.require_kernels()
        code, out = _env.run_main("reference_test")
        self.assertEqual(code, 0, out[-2000:])
        report = json.loads(
            (_env.HOME / "deep" / "REFERENCE_TESTS.json").read_text("utf-8")
        )
        self.assertEqual(report["R1_answer_key"]["result"], "DEFER")
        self.assertEqual(report["R2_crosswalk"]["verdict"], "DEFER")
        self.assertEqual(report["R5_pilot"], [])
        self.assertEqual(report["R4_read_only"]["result"], "PASS")
        self.assertTrue(all(c["result"] == "PASS" for c in report["R3_adversarial"]))

    def test_pilot_manifest_is_real_yaml(self):
        # a pilot file without a page must give YAML null, never the string "None"
        _env.require("yaml", "lxml")
        _env.require_kernels()
        import yaml

        rt = _env.engine("reference_test")
        folder = _env.HOME / "fixtures" / "pilot_probe"
        folder.mkdir(parents=True, exist_ok=True)
        raster = folder / "pilot #1 - page less.png"  # '#' and ' - ' need YAML quoting
        raster.write_bytes(_fixtures_png())
        pilot = [{"role": "control", "path": raster, "page": None}]
        with mock.patch.object(rt, "pilot_files", return_value=pilot):
            code, out = _env.run_main("reference_test")
        self.assertEqual(code, 0, out[-2000:])
        manifest = yaml.safe_load((rt.PILOT / "PILOT_MANIFEST.yaml").read_text("utf-8"))
        self.assertEqual(manifest["schema"], "gbogeb.estate.pilot/0.1")
        entry = manifest["files"][0]
        self.assertIsNone(entry["page"])
        self.assertEqual(entry["file"], raster.name)
        self.assertEqual(entry["sha256"], _sha(raster))

    def test_reviewed_pilot_labels_are_scored_against_the_current_graph(self):
        # reviewed labels must not keep passing once the input or the reader's graph has moved on
        _env.require("yaml", "lxml")
        _env.require_kernels()
        rt, dg = _env.engine("reference_test"), _env.engine("deep_graph")
        folder = _env.HOME / "fixtures" / "pilot_review"
        folder.mkdir(parents=True, exist_ok=True)
        svg = folder / "pilot_review.svg"
        svg.write_text(HEAD + BOXES + HOST + "</svg>", "utf-8")
        g = dg.read_svg(svg)
        page = g["edges"][0]["page"]
        pilot = [{"role": "pilot", "path": svg, "page": page}]
        lab = rt.PILOT / "labels" / "pilot_review.labels.json"
        lab.unlink(missing_ok=True)

        def score(graph):
            with mock.patch.object(rt, "pilot_files", return_value=pilot):
                return rt.r5_pilot({svg: graph})[0]

        self.assertEqual(score(g)["result"], "DEFER")
        labels = json.loads(lab.read_text("utf-8"))
        for o in labels["objects"]:
            o["truth"] = "ACCEPT"
        for e in labels["edges"]:
            e["truth"], e["direction"] = "ACCEPT", e["drawn_direction"]
        labels["status"] = "REVIEWED"
        lab.write_text(json.dumps(labels), "utf-8")
        self.assertEqual(score(g)["result"], "PASS")

        dropped = dict(g, edges=[e for e in g["edges"] if e["page"] != page])
        self.assertEqual(
            score(dropped)["result"], "FAIL", "accepted edge gone from the graph"
        )
        turned = dict(
            g,
            edges=[
                dict(
                    e,
                    direction="backward" if e["direction"] != "backward" else "forward",
                )
                for e in g["edges"]
            ],
        )
        self.assertEqual(score(turned)["result"], "FAIL", "graph direction changed")

        svg.write_text(HEAD + BOXES + "</svg>", "utf-8")
        stale = score(dg.read_svg(svg))
        self.assertEqual(stale["result"], "FAIL")
        self.assertIn("sha256", stale["why"])


def _fixtures_png() -> bytes:
    import base64

    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


class Promotion(unittest.TestCase):
    """thread_promote: a mycelium candidate reaches the golden thread only with authority, evidence and a typed relation."""

    def setUp(self):
        _env.require("yaml")
        self.tp = _env.engine("thread_promote")
        folder = _env.HOME / "promote_test"
        folder.mkdir(parents=True, exist_ok=True)
        self.saved = self.tp.MYC, self.tp.GOLD
        self.tp.MYC, self.tp.GOLD = folder / "candidates.jsonl", folder / "golden.jsonl"
        self.tp.GOLD.unlink(missing_ok=True)
        base = {
            "from": {"locator": "a#1"},
            "to": {"locator": "a#2"},
            "source_digest": "0" * 64,
            "drawn": "line",
            "drawn_direction": "none",
            "relation": "DEFER",
        }
        rows = [
            dict(
                base,
                statement="P-101 -- T-201",
                source_locator="a#e1",
                evidence="FILE_CONNECTED",
            ),
            dict(
                base,
                statement="P-101 -- T-202",
                source_locator="a#e2",
                evidence="GEOMETRIC_TOUCH",
            ),
        ]
        self.tp.MYC.write_text("".join(json.dumps(r) + "\n" for r in rows), "utf-8")

    def tearDown(self):
        self.tp.MYC, self.tp.GOLD = self.saved

    def _promote(self, *args):
        return _env.run_main("thread_promote", "promote", *args)

    def test_refusals(self):
        cases = {
            "no authority or evidence": ("a#e1", "--relation", "process_flow"),
            "relation still DEFER": (
                "a#e1",
                "--authority",
                "owner",
                "--evidence",
                "sheet 0",
            ),
            "geometry without review": (
                "a#e2",
                "--authority",
                "owner",
                "--evidence",
                "sheet 0",
                "--relation",
                "signal",
            ),
            "unknown candidate": (
                "a#e9",
                "--authority",
                "owner",
                "--evidence",
                "sheet 0",
                "--relation",
                "signal",
            ),
        }
        for why, args in cases.items():
            with self.subTest(case=why):
                code, out = self._promote(*args)
                self.assertEqual(code, 2, out)
                self.assertIn("REFUSED", out)
        self.assertFalse(self.tp.GOLD.exists())

    def test_accept_once(self):
        args = (
            "a#e1",
            "--authority",
            "owner",
            "--evidence",
            "sheet 0",
            "--relation",
            "process_flow",
        )
        code, out = self._promote(*args)
        self.assertEqual(code, 0, out)
        code, out = self._promote(*args)
        self.assertEqual(code, 2, out)
        self.assertIn("already in the golden thread", out)
        self.assertEqual(len(self.tp.GOLD.read_text("utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()

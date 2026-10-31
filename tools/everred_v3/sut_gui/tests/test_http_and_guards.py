"""Negative HTTP and data-readback QA for CODE PURPLE control tower."""

import importlib.util
import io
import json
import pathlib
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

FILE = pathlib.Path(__file__).resolve().parents[1] / "server.py"
spec = importlib.util.spec_from_file_location("sut_telemetry_guard", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SHA = "e" * 40


class SourceAndAPI(unittest.TestCase):
    def test_cache_retains_timestamp_and_revalidates_after_expiry(self):
        old = dict(mod.LIVE_CACHE)
        try:
            mod.LIVE_CACHE.update(time=0.0, result=None)
            with patch.object(
                mod,
                "live_snapshot",
                side_effect=[{"collected_at": "A"}, {"collected_at": "B"}],
            ) as native:
                with patch.object(
                    mod.time, "monotonic", side_effect=[10, 11, 700, 701]
                ):
                    self.assertEqual(mod.cached_live_snapshot()["collected_at"], "A")
                    self.assertEqual(mod.cached_live_snapshot()["collected_at"], "A")
                    self.assertEqual(mod.cached_live_snapshot()["collected_at"], "B")
                self.assertEqual(native.call_count, 2)
        finally:
            mod.LIVE_CACHE.update(old)

    def test_fetch_github_bounded_and_token_header(self):
        class Response:
            def __init__(self, data, status=200):
                self.data, self.status = data, status

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, n):
                return self.data

        class Opener:
            def __init__(self, result):
                self.result = result

            def open(self, req, timeout):
                self.req = req
                self.timeout = timeout
                return self.result

        with patch.object(
            mod.request, "build_opener", return_value=Opener(Response(b'{"ok":true}'))
        ) as maker:
            self.assertTrue(mod.fetch_github("/repos/x/y", "fake-test-token")["ok"])
            self.assertEqual(
                maker.return_value.req.get_header("Authorization"),
                "Bearer fake-test-token",
            )
            self.assertEqual(maker.return_value.timeout, 7)
        with patch.object(
            mod.request, "build_opener", return_value=Opener(Response(b"{}", 403))
        ):
            with self.assertRaises(OSError):
                mod.fetch_github("/repos/x/y", None)
        with patch.object(
            mod.request, "build_opener", return_value=Opener(Response(b"x" * 1_500_001))
        ):
            with self.assertRaisesRegex(OSError, "too large"):
                mod.fetch_github("/repos/x/y", None)
        with patch.object(
            mod.request, "build_opener", return_value=Opener(Response(b"not json"))
        ):
            with self.assertRaises(json.JSONDecodeError):
                mod.fetch_github("/repos/x/y", None)

    def test_early_reject_when_sut_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            mgr = mod.RunManager(pathlib.Path(tmp), execution_enabled=True)
            self.assertEqual(mgr.launch("unit-tests", mgr.token)[0], 400)
            mgr.active = "some-other-testflight"
            (pathlib.Path(tmp) / "src").mkdir()
            (pathlib.Path(tmp) / "src" / "everred.py").write_text("print(1)")
            self.assertEqual(mgr.launch("unit-tests", mgr.token)[0], 409)

    def test_get_routes_and_rejected_posts(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            manager = mod.RunManager(root, execution_enabled=False)
            handler = type(
                "HandlerQA",
                (mod.Handler,),
                {"manager": manager, "public_index": FILE.parent / "index.html"},
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with patch.object(
                    mod,
                    "cached_live_snapshot",
                    return_value={
                        "schema": "code-purple.live.v2",
                        "collected_at": "mock",
                    },
                ):
                    self.assertIn(
                        b"code-purple.ops-dashboard.v2", urlopen(base + "/").read()
                    )
                    status = json.load(urlopen(base + "/api/status"))
                    self.assertFalse(status["execution_enabled"])
                    self.assertEqual(
                        json.load(urlopen(base + "/api/live"))["collected_at"], "mock"
                    )
                    self.assertEqual(json.load(urlopen(base + "/api/runs"))["runs"], [])
                    for route in ["/api/runs/missing", "/not-a-real-route"]:
                        with self.assertRaises(HTTPError) as ctx:
                            urlopen(base + route)
                        self.assertEqual(ctx.exception.code, 404)
                    data = json.dumps({"profile": "unit-tests"}).encode()

                    def send(route, payload, origin, content_type="application/json"):
                        return urlopen(
                            Request(
                                base + route,
                                data=payload,
                                method="POST",
                                headers={
                                    "Origin": origin,
                                    "Content-Type": content_type,
                                    "X-SUT-Token": manager.token,
                                },
                            ),
                            timeout=5,
                        )

                    for route, payload, origin, kind, code in [
                        ("/bad", data, base, "application/json", 404),
                        ("/api/run", data, base, "text/plain", 415),
                        ("/api/run", b"", base, "application/json", 400),
                        ("/api/run", b"{", base, "application/json", 400),
                        (
                            "/api/run",
                            json.dumps({"profile": "unit-tests", "extra": 1}).encode(),
                            base,
                            "application/json",
                            400,
                        ),
                    ]:
                        with self.assertRaises(HTTPError) as ctx:
                            send(route, payload, origin, kind)
                        self.assertEqual(ctx.exception.code, code)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()

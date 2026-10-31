"""W45 real local Git checkout, authorization, clone, binary I/O and HTTP tests."""

import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HERE = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "w45_operator", HERE / "operator_workbench.py"
)
operator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operator_module)
app_spec = importlib.util.spec_from_file_location("w45_server", HERE / "server.py")
server_module = importlib.util.module_from_spec(app_spec)
app_spec.loader.exec_module(server_module)


@unittest.skipUnless(shutil.which("git"), "Git required for exact-head clone test")
class WorkbenchContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="w45-gui-qa-")
        self.base = pathlib.Path(self.temp.name)
        self.root = self.base / "ABACUS"
        self.root.mkdir()
        for folder in ("tests", "tools", "mission_control_lite"):
            (self.root / folder).mkdir()
        (self.root / "mission_control_lite" / "__init__.py").write_text("")
        (self.root / "tests" / "test_mission_control_lite.py").write_text(
            "import unittest\n"
            "class Basic(unittest.TestCase):\n"
            "    def test_meaningful_execution(self):\n"
            "        self.assertEqual(2+3, 5)\n"
        )
        (self.root / "tests" / "test_runner_wait.py").write_text(
            "import unittest\n"
            "class Basic(unittest.TestCase):\n"
            "    def test_runner_metadata(self):\n"
            "        self.assertTrue('runner')\n"
        )
        (self.root / "mission_control_lite" / "cli.py").write_text(
            "import pathlib,sys\n"
            "if __name__=='__main__':\n"
            "    dest=pathlib.Path(sys.argv[-1])\n"
            "    dest.parent.mkdir(parents=True,exist_ok=True)\n"
            "    dest.write_bytes(b'LOCAL_FAKE_RECEIPT')\n"
            "    print('READ_ONLY_CENSUS')\n"
        )
        (self.root / "tools" / "qps_binary_bridge.py").write_text(
            "import json,pathlib,sys\n"
            "source=pathlib.Path(sys.argv[1])\n"
            "output=pathlib.Path(sys.argv[sys.argv.index('--output')+1])\n"
            "output.parent.mkdir(parents=True,exist_ok=True)\n"
            "output.write_text(json.dumps({'original':source.name,'bytes':len(source.read_bytes())}))\n"
        )
        (self.root / "tools" / "generic_3p_pipeline.py").write_text(
            "import pathlib,sys\n"
            "out=pathlib.Path(sys.argv[sys.argv.index('--out-dir')+1])\n"
            "out.mkdir(parents=True,exist_ok=True)\n"
            "(out/'pipeline.json').write_text('{\"status\":\"PASS\"}')\n"
        )
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        for key, value in (
            ("user.email", "qa@example.invalid"),
            ("user.name", "W45 Unit QA"),
        ):
            subprocess.run(
                ["git", "-C", str(self.root), "config", key, value], check=True
            )
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-q", "-m", "fixture"], check=True
        )
        self.inbox = self.base / "inbox"
        self.inbox.mkdir()
        self.receipts = self.base / "receipts"
        self.manager = operator_module.OperatorWorkbench(
            self.root,
            self.inbox,
            self.receipts,
            enabled=True,
            token="w45-token",
            timeout_seconds=30,
        )
        self.sha = operator_module._git_head(self.root)
        self.assertEqual(len(self.sha), 40)

    def tearDown(self):
        self.temp.cleanup()

    def wait(self, rid):
        end = time.monotonic() + 25
        while time.monotonic() < end:
            row = self.manager.get_run(rid)
            if row["receipt_sha256"] is not None:
                return row
            time.sleep(0.04)
        self.fail("local testflight timed out")

    def submit(
        self,
        profile,
        filename=None,
        input_sha=None,
        delay=0,
        consent=True,
        sha=None,
        token="w45-token",
    ):
        return self.manager.submit(
            profile,
            filename,
            self.sha if sha is None else sha,
            input_sha,
            consent,
            delay,
            token,
        )

    def test_nonbinary_profiles_plan_without_binary_filename(self):
        # W45 native run 39173795497: eager binary command construction
        # raised TypeError for filename=None, surfacing as HTTP 400.
        for profile in (
            "python-tests",
            "runner-tests",
            "debug-compile",
            "task-census",
            "pipeline-3p",
        ):
            with self.subTest(profile=profile):
                plan = self.manager.plan(profile)
                self.assertTrue(plan["executable"])
                self.assertIsNone(plan["input"])
                self.assertEqual(plan["source_sha"], self.sha)
                self.assertNotIn("operator-input/None", repr(plan["argv"]))
                self.assertTrue(all(command[0] == "python" for command in plan["argv"]))
        with self.assertRaisesRegex(ValueError, "verified local input"):
            self.manager._steps("binary-bridge", None, self.sha)

    def test_profile_catalog_and_mcp_refusal(self):
        catalog = self.manager.catalog()
        self.assertEqual(catalog["source_sha"], self.sha)
        self.assertFalse(catalog["security_waiver"])
        self.assertEqual(len(catalog["profiles"]), 7)
        self.assertEqual(self.manager.plan("mcp-readiness")["executable"], False)
        self.assertEqual(self.submit("mcp-readiness")[0], 403)
        with self.assertRaises(ValueError):
            self.manager.plan("../../tmp")
        self.assertEqual(self.manager.list_runs(), [])

    def test_token_consent_identity_schedule_boundaries(self):
        self.assertEqual(self.submit("python-tests", token="incorrect")[0], 403)
        self.assertEqual(self.submit("python-tests", consent=False)[0], 403)
        self.assertEqual(self.submit("python-tests", sha="f" * 40)[0], 409)
        for bad in (-1, 3601, 1.5, True, "60"):
            with self.subTest(delay=bad):
                self.assertEqual(self.submit("python-tests", delay=bad)[0], 400)
        disabled = operator_module.OperatorWorkbench(
            self.root, self.inbox, self.receipts, token="w45-token"
        )
        self.assertEqual(
            disabled.submit("python-tests", None, self.sha, None, True, 0, "w45-token")[
                0
            ],
            403,
        )

    def test_clone_testflight_and_append_only_receipt(self):
        code, row = self.submit("python-tests")
        self.assertEqual(code, 202)
        final = self.wait(row["id"])
        self.assertEqual(final["status"], "PASS_LOCAL_ONLY", final["steps"])
        self.assertIn("test_mission_control_lite.py", " ".join(final["argv"][0]))
        self.assertEqual(final["source_sha"], self.sha)
        self.assertFalse(final["originals_modified"])
        self.assertEqual(final["merge_admission"], "HOLD")
        self.assertTrue((self.receipts / row["id"] / "receipt.json").exists())
        before = (self.receipts / row["id"] / "receipt.json").read_bytes()
        self.assertEqual(json.loads(before)["receipt_sha256"], final["receipt_sha256"])
        self.assertEqual(operator_module._git_head(self.root), self.sha)
        # Final receipts cannot be silently replaced on a duplicate finalize.
        with self.assertRaises(FileExistsError):
            self.manager._finalize(self.manager.records[row["id"]])

    def test_binary_input_copy_and_derived_receipt(self):
        original = self.inbox / "Test input.pdf"
        contents = b"%PDF-1.4\n1 0 obj\nendobj\n%%EOF\n"
        original.write_bytes(contents)
        plan = self.manager.plan("binary-bridge", original.name)
        self.assertEqual(plan["input"]["sha256"], hashlib.sha256(contents).hexdigest())
        code, row = self.submit("binary-bridge", original.name, plan["input"]["sha256"])
        self.assertEqual(code, 202)
        result = self.wait(row["id"])
        self.assertEqual(result["status"], "PASS_LOCAL_ONLY", result["steps"])
        self.assertEqual(original.read_bytes(), contents)
        self.assertEqual(len(result["artifacts"]), 1)
        art = result["artifacts"][0]
        path = self.receipts / row["id"] / art["path"]
        self.assertEqual(art["sha256"], operator_module.file_hash(path))
        self.assertEqual(self.manager.artifact(row["id"], 0)[1], path.read_bytes())
        self.assertEqual(json.loads(path.read_text())["original"], original.name)
        self.assertEqual(result["originals_disposition"], "KEEP_AWAIT_USER_APPROVAL")
        path.write_bytes(b"CORRUPTED_OUTPUT")
        self.assertIsNone(self.manager.artifact(row["id"], 0))

    def test_input_mutation_after_approval_is_rejected(self):
        original = self.inbox / "review.pdf"
        original.write_bytes(b"%PDF-1.4\nfirst\n")
        proof = self.manager.plan("binary-bridge", original.name)
        original.write_bytes(b"%PDF-1.4\nmodified\n")
        self.assertEqual(
            self.submit("binary-bridge", original.name, proof["input"]["sha256"])[0],
            409,
        )
        self.assertEqual(self.manager.list_runs(), [])

    def test_traversal_symlink_and_invalid_magic_rejected(self):
        for name in ("../secret.pdf", "/etc/hosts", "bad\\name.docx"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.manager.plan("binary-bridge", name)
        (self.inbox / "invalid.xlsx").write_bytes(b"NOT_A_ZIP")
        with self.assertRaisesRegex(ValueError, "OOXML ZIP"):
            self.manager.plan("binary-bridge", "invalid.xlsx")
        target = self.inbox / "ok.pdf"
        target.write_bytes(b"%PDF-1.4\n")
        link = self.inbox / "alias.pdf"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Symlink creation blocked by local Windows policy")
        self.assertNotIn(
            "alias.pdf", [item["name"] for item in self.manager.available_inputs()]
        )
        with self.assertRaises(ValueError):
            self.manager.plan("binary-bridge", "alias.pdf")

    def test_deferred_schedule_cancel_and_capacity(self):
        code, row = self.submit("runner-tests", delay=300)
        self.assertEqual(code, 202)
        self.assertEqual(row["status"], "SCHEDULED")
        self.assertEqual(self.submit("python-tests")[0], 409)
        self.assertEqual(self.manager.cancel(row["id"], "incorrect")[0], 403)
        done_code, done = self.manager.cancel(row["id"], "w45-token")
        self.assertEqual(done_code, 200)
        self.assertEqual(done["status"], "CANCELLED")
        self.assertIsNotNone(done["receipt_sha256"])
        self.assertEqual(self.manager.cancel(row["id"], "w45-token")[0], 409)
        status, next_row = self.submit("runner-tests")
        self.assertEqual(status, 202)
        self.assertEqual(self.wait(next_row["id"])["status"], "PASS_LOCAL_ONLY")

    def test_pipeline_runner_and_task_receipts(self):
        for profile, artifact_suffix in (
            ("pipeline-3p", "3p/pipeline.json"),
            ("task-census", "mcl.sqlite"),
        ):
            with self.subTest(profile=profile):
                code, row = self.submit(profile)
                self.assertEqual(code, 202)
                final = self.wait(row["id"])
                self.assertEqual(final["status"], "PASS_LOCAL_ONLY", final["steps"])
                self.assertTrue(
                    any(x["path"].endswith(artifact_suffix) for x in final["artifacts"])
                )
        code, row = self.submit("debug-compile")
        self.assertEqual(code, 202)
        self.assertEqual(self.wait(row["id"])["status"], "PASS_LOCAL_ONLY")


@unittest.skipUnless(shutil.which("git"), "Git required for end-to-end local server")
class OperatorHTTP(WorkbenchContracts):
    def test_loopback_negative_route_and_payload_branches(self):
        """W49: exercise actual uncovered W45 server denial branches.

        Derived from the native Python 3.10 coverage artifact of run 39176574449.
        All checks use a local ephemeral HTTP server and must leave the 80%
        *branch* coverage gate unchanged. No GitHub, arbitrary shell or
        security policy bypass is involved.
        """
        handler = type(
            "W49NegativeHandler",
            (server_module.Handler,),
            {
                "manager": server_module.RunManager(self.root),
                "operator": self.manager,
                "public_index": HERE / "index.html",
                "operator_page": HERE / "operator.html",
            },
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = "http://127.0.0.1:" + str(server.server_port)

        def http_status(route, body=None, headers=None):
            opts = dict(headers or {})
            if body is not None:
                opts.setdefault("Origin", base)
                opts.setdefault("Content-Type", "application/json")
            # Explicit loopback-only transport: no caller-supplied URI scheme
            # or dynamic URL open. This is a native HTTP denial-path test.
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=7)
            try:
                conn.request(
                    "POST" if body is not None else "GET",
                    route,
                    body=body,
                    headers=opts,
                )
                response = conn.getresponse()
                response.read()
                return response.status
            finally:
                conn.close()

        try:
            self.assertEqual(http_status("/api/status"), 200)
            self.assertEqual(http_status("/api/operator/runs/not-present"), 404)
            self.assertEqual(http_status("/api/runs/not-present"), 404)
            self.assertEqual(http_status("/api/operator/unknown"), 404)
            self.assertEqual(
                http_status(
                    "/api/operator/artifacts/malformed",
                    headers={"X-SUT-Token": "w45-token"},
                ),
                404,
            )
            self.assertEqual(http_status("/api/unknown", body=b"{}"), 404)
            self.assertEqual(
                http_status(
                    "/api/operator/plan",
                    body=b'{"profile":"python-tests"}',
                    headers={"Host": "attacker.invalid"},
                ),
                403,
            )
            self.assertEqual(
                http_status(
                    "/api/operator/plan",
                    body=b'{"profile":"python-tests"}',
                    headers={"Content-Type": "text/plain"},
                ),
                415,
            )
            for payload in (
                b"",
                b"[]",
                b'{"profile":"python-tests","extra":1}',
                b'{"profile":"../../invalid"}',
                b"{}",
            ):
                with self.subTest(payload=payload):
                    self.assertEqual(
                        http_status("/api/operator/plan", body=payload), 400
                    )
        finally:
            server.shutdown()
            server.server_close()

    def test_loopback_api_plan_consent_run_cancel_and_html(self):
        handler = type(
            "OperatorTestHandler",
            (server_module.Handler,),
            {
                "manager": server_module.RunManager(self.root),
                "operator": self.manager,
                "public_index": HERE / "index.html",
                "operator_page": HERE / "operator.html",
            },
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:" + str(server.server_port)

        def post(route, obj, origin=None, token=None):
            headers = {
                "Content-Type": "application/json",
                "Origin": base if origin is None else origin,
            }
            if token is not None:
                headers["X-SUT-Token"] = token
            req = Request(
                base + route,
                data=json.dumps(obj).encode(),
                headers=headers,
                method="POST",
            )
            return urlopen(req, timeout=7)

        try:
            page = urlopen(base + "/operator").read()
            self.assertIn(b"codepurple.operator.workbench.v1", page)
            self.assertIn(b"Operator Workbench", page)
            info = json.load(urlopen(base + "/api/operator/catalog"))
            self.assertTrue(info["execution_enabled"])
            self.assertEqual(info["source_sha"], self.sha)
            with self.assertRaises(HTTPError) as bad_host:
                urlopen(
                    Request(
                        base + "/api/operator/catalog",
                        headers={"Host": "attacker.invalid"},
                    )
                )
            self.assertEqual(bad_host.exception.code, 403)
            with self.assertRaises(HTTPError) as foreign:
                post(
                    "/api/operator/plan",
                    {"profile": "python-tests"},
                    origin="http://evil.invalid",
                )
            self.assertEqual(foreign.exception.code, 403)
            plan = json.load(post("/api/operator/plan", {"profile": "python-tests"}))[
                "result"
            ]
            self.assertEqual(plan["source_sha"], self.sha)
            request = {
                "profile": "python-tests",
                "input_name": None,
                "source_sha": plan["source_sha"],
                "input_sha256": None,
                "consent": True,
                "after_seconds": 0,
            }
            with self.assertRaises(HTTPError) as no_token:
                post("/api/operator/run", request)
            self.assertEqual(no_token.exception.code, 403)
            request["consent"] = False
            with self.assertRaises(HTTPError) as no_consent:
                post("/api/operator/run", request, token="w45-token")
            self.assertEqual(no_consent.exception.code, 403)
            request["consent"] = True
            row = json.load(post("/api/operator/run", request, token="w45-token"))[
                "result"
            ]
            self.assertEqual(self.wait(row["id"])["status"], "PASS_LOCAL_ONLY")
            retrieved = json.load(urlopen(base + "/api/operator/runs/" + row["id"]))
            self.assertEqual(
                retrieved["receipt_sha256"],
                self.manager.get_run(row["id"])["receipt_sha256"],
            )
            # Generated artifacts are private to token-bearing local readbacks.
            stat = json.load(
                post(
                    "/api/operator/run",
                    {
                        **request,
                        "profile": "task-census",
                    },
                    token="w45-token",
                )
            )["result"]
            finished = self.wait(stat["id"])
            self.assertEqual(finished["status"], "PASS_LOCAL_ONLY")
            artifact_route = base + "/api/operator/artifacts/" + stat["id"] + "/0"
            with self.assertRaises(HTTPError) as absent_token:
                urlopen(artifact_route, timeout=5)
            self.assertEqual(absent_token.exception.code, 403)
            authorized = Request(artifact_route, headers={"X-SUT-Token": "w45-token"})
            self.assertEqual(
                urlopen(authorized, timeout=5).read(), b"LOCAL_FAKE_RECEIPT"
            )
            with self.assertRaises(HTTPError) as missing_output:
                urlopen(
                    Request(
                        base + "/api/operator/artifacts/" + stat["id"] + "/999",
                        headers={"X-SUT-Token": "w45-token"},
                    ),
                    timeout=5,
                )
            self.assertEqual(missing_output.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()


class OperatorSurfaceQA(unittest.TestCase):
    def test_html_semantics_and_no_eval_escape(self):
        from html.parser import HTMLParser

        class Scan(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = []
                self.h1 = 0
                self.title = 0
                self.scripts = []
                self.in_script = False

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if "id" in attrs:
                    self.ids.append(attrs["id"])
                if tag == "h1":
                    self.h1 += 1
                if tag == "title":
                    self.title += 1
                if tag == "script":
                    self.in_script = True

            def handle_endtag(self, tag):
                if tag == "script":
                    self.in_script = False

            def handle_data(self, data):
                if self.in_script:
                    self.scripts.append(data)

        html = (HERE / "operator.html").read_text(encoding="utf-8")
        parser = Scan()
        parser.feed(html)
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertEqual(parser.h1, 1)
        self.assertEqual(parser.title, 1)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertIn("token", parser.ids)
        self.assertIn("consent", parser.ids)
        self.assertIn("downloads", parser.ids)
        script = "\n".join(parser.scripts)
        self.assertNotIn("eval(", script)
        self.assertNotIn("new Function(", script)
        self.assertIn("/api/operator/plan", script)
        self.assertIn("input_sha256", script)
        self.assertIn("/api/operator/artifacts/", script)
        if shutil.which("node"):
            completed = subprocess.run(
                ["node", "--check"],
                input=script,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import pathlib
import tempfile
import time
import unittest
from unittest.mock import patch

MOD = pathlib.Path(__file__).resolve().parents[1] / 'server.py'
spec = importlib.util.spec_from_file_location('sut_server', MOD)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LocalSUT(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / 'src').mkdir()
        (self.root / 'tests').mkdir()
        (self.root / 'src' / 'everred.py').write_text('print("LEDGER_VALID")\n')
        (self.root / 'tests' / 'test_demo.py').write_text('import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n')

    def tearDown(self):
        self.tmp.cleanup()

    def wait(self, manager, rid):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = manager.records[rid]
            if result['status'] != 'RUNNING':
                return result
            time.sleep(.02)
        self.fail('execution not terminal')

    def test_disabled_refuses(self):
        manager = mod.RunManager(self.root)
        status, message = manager.launch('ledger-verify', manager.token)
        self.assertEqual(status, 403)
        self.assertEqual(manager.records, {})

    def test_invalid_token_and_profile_refused(self):
        manager = mod.RunManager(self.root, execution_enabled=True)
        self.assertEqual(manager.launch('ledger-verify', 'bad')[0], 403)
        self.assertEqual(manager.launch('../anything', manager.token)[0], 400)
        self.assertFalse(manager.records)

    def test_allowlisted_sut_executes_in_temp(self):
        manager = mod.RunManager(self.root, execution_enabled=True)
        code, receipt = manager.launch('unit-tests', manager.token)
        self.assertEqual(code, 202)
        final = self.wait(manager, receipt['id'])
        self.assertEqual(final['status'], 'PASS_LOCAL_ONLY')
        self.assertEqual(final['commands'][0]['exit_code'], 0)
        self.assertTrue(final['receipt_sha256'])
        self.assertFalse(final['merge_authorized'])
        self.assertFalse((self.root / 'tests' / '__pycache__').exists())

    def test_no_tests_rejected(self):
        (self.root / 'tests' / 'test_demo.py').unlink()
        manager = mod.RunManager(self.root, execution_enabled=True)
        status, rec = manager.launch('unit-tests', manager.token)
        self.assertEqual(status, 202)
        end = self.wait(manager, rec['id'])
        self.assertEqual(end['status'], 'RED')
        self.assertIn('no tests executed', '\n'.join(end['logs']))

    def test_unknown_remote_evidence_stays_unknown(self):
        with patch.object(mod, 'fetch_github', side_effect=OSError('offline')):
            r = mod.live_snapshot()
        self.assertIsNone(r['repositories']['GBOGEB/ABACUS']['sha'])
        self.assertIsNone(r['ruleset']['rule_count'])
        self.assertGreaterEqual(len(r['errors']), 4)

    def test_api_redirect_refused(self):
        with self.assertRaisesRegex(OSError, "redirect refused"):
            mod._NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.example/")

    def test_http_origin_and_token_enforced(self):
        import json
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError

        manager = mod.RunManager(self.root, execution_enabled=True)
        cls = type('TestHandler', (mod.Handler,), {'manager': manager})
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), cls)
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        try:
            address = 'http://127.0.0.1:' + str(httpd.server_port)
            body = json.dumps({'profile': 'ledger-verify'}).encode()
            def post(origin, token):
                req = Request(address + '/api/run', data=body, headers={
                    'Content-Type': 'application/json',
                    'Origin': origin,
                    'X-SUT-Token': token}, method='POST')
                return urlopen(req, timeout=5)
            with self.assertRaises(HTTPError) as wrong_origin:
                post('http://foreign.example', manager.token)
            self.assertEqual(wrong_origin.exception.code, 403)
            with self.assertRaises(HTTPError) as wrong_token:
                post(address, 'wrong')
            self.assertEqual(wrong_token.exception.code, 403)
            result = json.loads(post(address, manager.token).read())
            self.assertEqual(self.wait(manager, result['result']['id'])['status'], 'PASS_LOCAL_ONLY')
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_symlink_rejected(self):
        (self.root / 'src' / 'unsafe.py').symlink_to(self.root / 'tests' / 'test_demo.py')
        manager = mod.RunManager(self.root, execution_enabled=True)
        code, receipt = manager.launch('ledger-verify', manager.token)
        self.assertEqual(code, 202)
        end = self.wait(manager, receipt['id'])
        self.assertEqual(end['status'], 'ERROR')
        self.assertIn('Symlink not allowed', '\n'.join(end['logs']))


if __name__ == '__main__':
    unittest.main()

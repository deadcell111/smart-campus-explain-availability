"""Integration tests over real HTTP against server.py (ephemeral ports)."""
import http.client
import json
import threading
import unittest

import _path  # noqa: F401
from server import make_server


class Srv:
    def __init__(self, mode="mock", timeout=0.3):
        self.srv = make_server(mode, timeout)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.port = self.srv.server_address[1]

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, data

    def explain(self, start="12:00", end="13:00", blocked=False):
        st, data = self.req("POST", "/api/explain", json.dumps({"start": start, "end": end, "blocked": blocked}),
                            {"Content-Type": "application/json"})
        return st, json.loads(data)


class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Srv("mock")

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def test_serves_page_with_explain_button(self):
        st, data = self.s.req("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn(b'id="explainBtn"', data)

    def test_available_roundtrip(self):
        st, r = self.s.explain("12:00", "13:00")
        self.assertEqual((st, r["decision"]["label"], r["explanation"]["source"]), (200, "Available", "mock"))

    def test_each_reason_code(self):
        cases = [("10:30", "11:30", False, "overlap"), ("12:00", "13:00", True, "blocked"), ("12:00", "11:00", False, "range"),
                 ("08:00", "09:00", False, "past"), ("14:00", "16:30", False, "long")]
        for s, e, b, code in cases:
            st, r = self.s.explain(s, e, b)
            self.assertEqual((st, r["decision"]["reasonCode"]), (200, code))
            self.assertEqual(r["explanation"]["source"], "mock", code)

    def test_empty_malformed_long_rejected(self):
        h = {"Content-Type": "application/json"}
        self.assertEqual(self.s.req("POST", "/api/explain", b"", h)[0], 400)
        self.assertEqual(self.s.req("POST", "/api/explain", b"not json", h)[0], 400)
        self.assertEqual(self.s.req("POST", "/api/explain", b"x" * 5000, h)[0], 413)
        self.assertEqual(self.s.explain("12:00; DROP TABLE", "13:00")[0], 400)

    def test_unknown_paths_404_and_no_traversal(self):
        self.assertEqual(self.s.req("GET", "/../booking.py")[0], 404)
        self.assertEqual(self.s.req("GET", "/booking.py")[0], 404)
        self.assertEqual(self.s.req("POST", "/other", b"{}")[0], 404)


class TestFailureModesOverHttp(unittest.TestCase):
    def check(self, mode):
        s = Srv(mode, 0.3)
        try:
            st, r = s.explain("12:00", "13:00")
            self.assertEqual((st, r["decision"]["label"], r["explanation"]["source"]), (200, "Available", "fallback"))
        finally:
            s.close()

    def test_api_error(self):
        self.check("mock:fail")

    def test_timeout(self):
        self.check("mock:timeout")

    def test_contradicting_output(self):
        self.check("mock:bad")

    def test_markup_output(self):
        self.check("mock:inject")

    def test_anthropic_without_key(self):
        import os
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            self.check("anthropic")
        finally:
            if old:
                os.environ["ANTHROPIC_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()

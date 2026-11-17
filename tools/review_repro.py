"""Reproduction scripts for the review hypotheses (H1-H8). Each returns (verdict, evidence).
Run: python3 -I tools/review_repro.py [label]   -> prints a table and writes evidence/review_repro_<label>.txt"""
import contextlib, http.client, io, json, os, pathlib, re, socket, sys, threading, time, types
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import explain as ex
from reasons import EXISTING
from server import make_server

body = lambda s="12:00", e="13:00", b=False: json.dumps({"start": s, "end": e, "blocked": b}).encode()
F = lambda code, ok, s="12:00", e="13:00": {"roomLabel": "Room B-204", "start": s, "end": e, "isAvailable": ok, "reasonCode": code}


def h1_validator_accepts_contradiction():
    cases = [(F("long", False, "14:00", "16:30"), "Good to go: this is yours for 14:00-16:30, even though it is longer than the maximum."),
             (F("overlap", False, "10:30", "11:30"), "No problem, the room is all yours at 10:30-11:30, it already has other bookings.")]
    accepted = []
    for facts, text in cases:
        try:
            ex.validate_output({"explanation": text}, facts); accepted.append(text)
        except ex.OutputRejected:
            pass
    return ("CONFIRMED" if accepted else "NOT REPRODUCED",
            f"{len(accepted)}/{len(cases)} contradictory explanations of UNAVAILABLE results were accepted")


def h2_pool_starvation():
    class Slow:
        source = "mock"
        def complete(self, s, u): time.sleep(1.5); return "{}"
    ts = [threading.Thread(target=lambda: ex.explain(body(), Slow(), timeout=0.2)) for _ in range(6)]
    for t in ts: t.start()
    time.sleep(0.3)
    r = ex.explain(body(), ex.MockAdapter("ok"), timeout=0.5)       # a perfectly healthy request
    for t in ts: t.join()
    starved = r["explanation"]["source"] == "fallback"
    return ("CONFIRMED" if starved else "NOT REPRODUCED",
            f"healthy request while 6 slow calls were pending -> source={r['explanation']['source']}, note={r['explanation']['note']}")


def h3_slow_body_hangs_server_thread():
    s = make_server("mock", 0.3); threading.Thread(target=s.serve_forever, daemon=True).start()
    c = socket.create_connection(("127.0.0.1", s.server_address[1]))
    c.sendall(b"POST /api/explain HTTP/1.1\r\nHost: x\r\nContent-Length: 100\r\nContent-Type: application/json\r\n\r\n{\"start\"")
    c.settimeout(2.5)
    try:
        got = c.recv(100); verdict = ("NOT REPRODUCED", f"server answered: {got[:40]!r}")
    except socket.timeout:
        verdict = ("CONFIRMED", "after 2.5 s the server is still waiting for the missing body bytes (no socket timeout on the handler thread)")
    c.close(); s.shutdown(); return verdict


def h4_false_rejection_of_negations():
    ok_texts = ["Room B-204 is free from 12:00 to 13:00 and does not overlap any booking.", "Good news, the room is free and it is not blocked."]
    rejected = []
    for t in ok_texts:
        try: ex.validate_output({"explanation": t}, F("ok", True))
        except ex.OutputRejected: rejected.append(t)
    return ("CONFIRMED" if rejected else "NOT REPRODUCED", f"{len(rejected)}/{len(ok_texts)} correct explanations of an AVAILABLE slot were rejected (safe fallback shown instead)")


def h5_xss_in_ui():
    import threading as th
    from playwright.sync_api import sync_playwright
    s = make_server("mock", 0.3); th.Thread(target=s.serve_forever, daemon=True).start()
    evil = '<img src=x onerror="window.__xss=1">Room is free'
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless=True); pg = b.new_page()
        pg.route("**/api/explain", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(
            {"decision": {"isAvailable": True, "reasonCode": "ok", "label": "Available"}, "explanation": {"text": evil, "source": "llm", "generated": True, "note": None}, "disclaimer": "d"})))
        pg.goto(f"http://127.0.0.1:{s.server_address[1]}/"); pg.fill("#start", "12:00"); pg.fill("#end", "13:00"); pg.click("button[type=submit]"); pg.click("#explainBtn")
        pg.wait_for_selector("#explainOut:not([hidden])"); time.sleep(0.3)
        img = pg.query_selector("#explainText img"); flag = pg.evaluate("window.__xss === 1"); shown = pg.inner_text("#explainText"); b.close()
    s.shutdown()
    return ("UNSUPPORTED" if not img and not flag else "CONFIRMED", f"img element injected: {bool(img)}, script flag set: {flag}; text shown literally: {shown[:30]!r}")


def h6_secret_leak():
    secret = "FAKE-KEY-1234"
    fake = types.ModuleType("anthropic")
    class Boom:
        def __init__(self, **kw): self.messages = self
        def create(self, **kw): raise RuntimeError("auth failed for key " + secret)
    fake.Anthropic = Boom
    sys.modules["anthropic"] = fake; os.environ["ANTHROPIC_API_KEY"] = secret
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            r = ex.explain(body(), ex.AnthropicAdapter(0.5), timeout=1)
    finally:
        del sys.modules["anthropic"]; os.environ.pop("ANTHROPIC_API_KEY", None)
    leaked = secret in json.dumps(r) or secret in err.getvalue()
    return ("UNSUPPORTED" if not leaked else "CONFIRMED", f"secret in response/log: {leaked}; note={r['explanation']['note']!r}; source={r['explanation']['source']}")


def h7_path_traversal():
    s = make_server("mock", 0.3); threading.Thread(target=s.serve_forever, daemon=True).start()
    codes = {}
    for path in ("/%2e%2e/booking.py", "/../booking.py", "/explain.py", "/index.html/../server.py", "/app/server.py"):
        c = http.client.HTTPConnection("127.0.0.1", s.server_address[1]); c.request("GET", path); codes[path] = c.getresponse().status; c.close()
    s.shutdown()
    return ("UNSUPPORTED" if all(v == 404 for v in codes.values()) else "CONFIRMED", "statuses " + json.dumps(codes))


def h8_duplicated_rules_and_data():
    html = (ROOT / "app" / "index.html").read_text()
    m = re.findall(r"start: (\d+), end: (\d+)", html); data_same = tuple((int(a), int(b)) for a, b in m) == tuple(EXISTING)
    copies = {f: len(re.findall(r"< ?b[._]?[eE]nd", (ROOT / "app" / f).read_text())) for f in ("booking.py", "reasons.py", "index.html")}
    return ("CONFIRMED (design risk, no defect today)", f"overlap predicate written in {sum(1 for v in copies.values() if v)} files {copies}; booking data duplicated in index.html and reasons.py (currently equal: {data_same})")


HYP = [("H1", "Output validator accepts explanations that contradict an UNAVAILABLE status", h1_validator_accepts_contradiction),
       ("H2", "Shared 4-thread pool: slow/timed-out calls starve healthy requests", h2_pool_starvation),
       ("H3", "No socket timeout: a client that sends a short body pins a server thread", h3_slow_body_hangs_server_thread),
       ("H4", "Validator rejects correct 'no overlap / not blocked' wording", h4_false_rejection_of_negations),
       ("H5", "Model output can inject HTML/script in the UI", h5_xss_in_ui),
       ("H6", "API key or provider error text can leak to the client/logs", h6_secret_leak),
       ("H7", "Static file server allows path traversal to source files", h7_path_traversal),
       ("H8", "Rules and data are duplicated across files (drift risk)", h8_duplicated_rules_and_data)]
if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "before"
    lines = []
    for hid, title, fn in HYP:
        with contextlib.redirect_stderr(io.StringIO()):
            v, e = fn()
        lines.append(f"{hid} | {v} | {title}\n     evidence: {e}")
    text = "\n".join(lines); print(text); (ROOT / "evidence" / f"review_repro_{label}.txt").write_text(text + "\n")

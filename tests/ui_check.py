"""UI / integration checks in headless Chrome (Playwright). Run: python3 -I tests/ui_check.py  (saves shots/)"""
import pathlib, sys, threading
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from playwright.sync_api import sync_playwright
from server import make_server

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
results = []


def check(name, cond, detail=""):
    results.append(bool(cond)); print("PASS" if cond else "FAIL", name, ("-> " + str(detail)) if detail else "")


def serve(mode, timeout=0.4):
    s = make_server(mode, timeout); threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}/"


def submit(pg, s, e, blocked=False):
    pg.set_checked("#blockedToggle", blocked); pg.fill("#start", s); pg.fill("#end", e); pg.click("button[type=submit]")


def explain(pg):
    pg.click("#explainBtn"); pg.wait_for_selector("#explainOut:not([hidden])", timeout=8000)
    return pg.inner_text("#explainText"), pg.inner_text("#explainSrc")


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    pg = b.new_page(viewport={"width": 375, "height": 800})
    errors = []; pg.on("pageerror", lambda e: errors.append(str(e)))
    srv, url = serve("mock")

    # --- AC1 regression: the original UI cases (same as the baseline UI check) on the modified page
    reg = [("base free", "12:00", "13:00", False, "Available"), ("touching 11:00-12:00", "11:00", "12:00", False, "Available"),
           ("overlap 10:30-11:30", "10:30", "11:30", False, "Unavailable"), ("blocked 11:00-12:00", "11:00", "12:00", True, "Unavailable"),
           ("exactly 120 (11:00-13:00)", "11:00", "13:00", False, "Available"), ("121 min (14:30-16:31)", "14:30", "16:31", False, "Unavailable"),
           ("starts now 09:00-09:30", "09:00", "09:30", False, "Unavailable"), ("reversed 12:00-11:00", "12:00", "11:00", False, "Unavailable"),
           ("empty inputs", "", "", False, "Enter both times")]
    pg.goto(url)
    for n, s, e, blk, exp in reg:
        submit(pg, s, e, blk); check("REG " + n, pg.inner_text("#result .big") == exp, pg.inner_text("#result .big"))

    # --- new feature, normal path
    pg.goto(url); submit(pg, "12:00", "13:00")
    check("U01 explain button visible after a check", pg.is_visible("#explainBtn"))
    before = pg.inner_html("#result"); text, src = explain(pg)
    check("U02 available: explanation shown, mock source labelled", "free" in text and "Mock" in src, f"{src} | {text}")
    check("U03 result card unchanged by explanation (AC1/AC2)", pg.inner_html("#result") == before)
    check("U04 explanation visually/verbally distinct from status (AC5)", "ai-generated" in pg.inner_text("#explainOut").lower() and "not a booking confirmation" in pg.inner_text("#explainNote"))
    pg.screenshot(path=str(ROOT / "shots/ui_available_explained.png"), full_page=True)

    submit(pg, "10:30", "11:30"); before = pg.inner_html("#result"); text, _ = explain(pg)
    check("U05 overlap: agrees with Unavailable, no invented times", "overlap" in text and "17:" not in text and pg.inner_html("#result") == before, text)
    pg.screenshot(path=str(ROOT / "shots/ui_overlap_explained.png"), full_page=True)
    submit(pg, "12:00", "13:00", True); text, _ = explain(pg)
    check("U06 blocked room: explanation says blocked", "blocked" in text, text)
    pg.screenshot(path=str(ROOT / "shots/ui_blocked_explained.png"), full_page=True)
    submit(pg, "12:00", "11:00"); text, _ = explain(pg); check("U07 invalid time (end before start)", "end time" in text, text)
    submit(pg, "09:00", "09:30"); text, _ = explain(pg); check("U08 past/now start", "start time" in text, text)
    submit(pg, "14:00", "16:30"); text, _ = explain(pg); check("U09 over 120 minutes", "120" in text, text)

    submit(pg, "", ""); check("U10 empty input: no explain button offered", not pg.is_visible("#explainBtn"))
    submit(pg, "12:00", "13:00"); explain(pg); pg.fill("#end", "14:00")
    check("U11 editing an input hides the now-stale explanation", not pg.is_visible("#explainOut") and not pg.is_visible("#explainBtn"))
    srv.shutdown()

    # --- failure modes: decision stays, safe fallback, labelled
    for mode, label in [("mock:fail", "U12 simulated API error"), ("mock:timeout", "U13 timeout"), ("mock:bad", "U14 contradicting model output"), ("mock:inject", "U15 markup/instruction in model output")]:
        s2, u2 = serve(mode); pg.goto(u2); submit(pg, "12:00", "13:00"); before = pg.inner_html("#result"); text, src = explain(pg)
        check(label + ": fallback shown, decision unchanged", "Standard message" in src and text.startswith("Available:") and pg.inner_html("#result") == before, f"{src} | {text}")
        if mode == "mock:fail": pg.screenshot(path=str(ROOT / "shots/ui_api_failure_fallback.png"), full_page=True)
        if mode == "mock:timeout": pg.screenshot(path=str(ROOT / "shots/ui_timeout_fallback.png"), full_page=True)
        s2.shutdown()

    # --- no server at all (page opened from file://)
    pg.goto((ROOT / "app" / "index.html").as_uri()); submit(pg, "10:30", "11:30"); before = pg.inner_html("#result"); text, src = explain(pg)
    check("U16 no server (file://): safe message, decision unchanged", "not available right now" in text and pg.inner_html("#result") == before, text)
    check("U17 original rules still work without the server", pg.inner_text("#result .big") == "Unavailable")
    check("U18 no horizontal scroll at 375px", pg.evaluate("document.documentElement.scrollWidth") <= 375)
    check("U19 no JS page errors", not errors, errors)
    b.close()
print("total", len(results), "passed", sum(results), "failed", len(results) - sum(results))
sys.exit(0 if all(results) else 1)

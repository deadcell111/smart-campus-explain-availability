"""Builds report/Practice11_Report.pdf from the evidence files. Run: python3 tools/make_report.py (needs reportlab + Pillow)"""
import re, subprocess
from pathlib import Path
from PIL import Image as PI
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
rd = lambda p: (ROOT / p).read_text(encoding="utf-8")
run = rd("evidence/final_test_run.txt")
ran = [int(x) for x in re.findall(r"^Ran (\d+) tests", run, re.M)]
base_n, new_n = ran[0], ran[1]
ui_tot, ui_pass = map(int, re.search(r"total (\d+) passed (\d+)", run).groups())
assert "ALL CHECKS PASSED" in run and ui_tot == ui_pass
cases = [l for l in rd("evidence/test_cases.md").splitlines() if l.startswith("| C")]
cases_pass = sum("| PASS |" in l for l in cases)
before = rd("evidence/review_repro_before.txt"); after = rd("evidence/review_repro_after.txt")
verd = lambda txt, h: re.search(rf"^{h} \| ([^|\n]+?) \|", txt, re.M).group(1).strip()
diff = rd("review/review_input.diff")
idx_add = sum(1 for l in diff.split("diff -ruN")[1].splitlines() if l.startswith("+") and not l.startswith("+++"))
idx_del = sum(1 for l in diff.split("diff -ruN")[1].splitlines() if l.startswith("-") and not l.startswith("---"))
loc = {f: len(rd("app/" + f).splitlines()) for f in ("reasons.py", "explain.py", "server.py", "explain-client.js")}

S = getSampleStyleSheet()
B = ParagraphStyle("B", parent=S["BodyText"], fontSize=9.2, leading=12.4, spaceAfter=4)
SM = ParagraphStyle("SM", parent=B, fontSize=8, leading=10.2)
H1 = ParagraphStyle("H1", parent=S["Heading1"], fontSize=15, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=S["Heading2"], fontSize=11.5, spaceBefore=9, spaceAfter=3, textColor=colors.HexColor("#1f4fd8"))
H3 = ParagraphStyle("H3", parent=S["Heading3"], fontSize=9.8, spaceBefore=5, spaceAfter=2)
CODE = ParagraphStyle("C", fontName="Courier", fontSize=7.4, leading=9, backColor=colors.HexColor("#f4f6fa"), borderPadding=3, spaceAfter=5)
P = lambda t, s=B: Paragraph(t, s)
M = lambda t: f"<font face='Courier'>{t}</font>"


def tbl(rows, widths, fs=7.8):
    cell = ParagraphStyle("cell", parent=B, fontSize=fs, leading=fs + 2.2, spaceAfter=0)
    t = Table([[Paragraph(str(c), cell) for c in r] for r in rows], colWidths=[w * mm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d1e0")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6ecfb")), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    return t


def img(name, w):
    iw, ih = PI.open(ROOT / "shots" / name).size
    return Image(str(ROOT / "shots" / name), width=w * mm, height=w * mm * ih / iw)


R = [P("Practice #11 - Build a small AI-enabled feature (\"Explain availability\")", H1),
     P("<b>Student:</b> Talgat Kozhakhmetov | <b>ID:</b> 24B031852 | <b>Class:</b> Tuesday 13:00 - 16:00 (as in my Assignment #03 report)<br/>"
       "<b>AI tool:</b> Claude Code (CLI agent), model Claude Sonnet 5.5 (<font face='Courier'>claude-sonnet-5-5</font>), used on 2026-11-17<br/>"
       "<b>Project:</b> Smart Campus Room Availability Checker, one fictional room, no login, no database. "
       "<b>Live demo link:</b> not available (not published); run locally with the commands in README.md."),
     P("<b>Honesty statement.</b> Every result below comes from commands that were actually run (outputs in <font face='Courier'>evidence/</font>; "
       "<font face='Courier'>bash run_all_tests.sh</font> repeats them). No ANTHROPIC_API_KEY was available, so the feature runs with the "
       "<b>clearly labelled mock adapter</b>. A real Claude adapter is implemented but <b>was not run against the live API</b>; only its failure paths "
       "(no key, SDK missing, simulated error with a secret in the message) were exercised. The prompt comparison therefore has no live model results (Task 4)."),

     P("Task 1 - Baseline", H2),
     P("The final Smart Campus project (my Assignment #03 code) was copied to <font face='Courier'>baseline/</font> as a checkpoint and its SHA-256 hashes recorded "
       "(<font face='Courier'>evidence/00_baseline_checksums.txt</font>). Nothing in it was edited."),
     tbl([["Item", "Result"],
          ["Existing tests (cd baseline &amp;&amp; python3 -m unittest -v test_booking)", f"Ran {base_n} tests, OK"],
          ["Build", "None: no build step exists (plain HTML + Python)"],
          ["Lint", "No linter is configured or installed (flake8, pylint, eslint absent). Used instead: <font face='Courier'>python3 -m py_compile</font> and <font face='Courier'>node --check</font> on the extracted inline script: both OK"],
          ["Availability function", "<font face='Courier'>booking.py: can_book(start, end, now, blocked, existing)</font>; browser copy <font face='Courier'>index.html: evaluate()</font>"],
          ["UI component", "<font face='Courier'>index.html</font> form, <font face='Courier'>#result</font> card and submit handler"],
          ["Repository instructions", "None existed in the baseline. I wrote <font face='Courier'>AGENTS.md</font> (hard rules, layout, commands) and README.md before the review"],
          ["Constraints kept", "one room (B-204), fictional bookings, no login, no database"]], [62, 112]),

     P("Task 2 - Feature definition", H2),
     P("<b>User story.</b> As a student, I want a short explanation of room availability so I understand the decision."),
     tbl([["Part", "Definition"],
          ["Input (browser to server)", "POST /api/explain, JSON, at most 512 bytes, exactly {start: \"HH:MM\", end: \"HH:MM\", blocked: boolean}. The room label is fixed on the server and never taken from the client."],
          ["Facts sent to the model", "{roomLabel, start, end, isAvailable, reasonCode}; reasonCode is one of ok, blocked, range, past, long, overlap. No booking list or personal data."],
          ["Model output", "{\"explanation\": string}, at most 2 sentences and 280 characters; treated as untrusted and validated."],
          ["Response", "{decision{isAvailable, reasonCode, label}, explanation{text, source: mock|llm|fallback, generated}, disclaimer}"],
          ["Failure behaviour", "bad input: HTTP 400/413, no model call. Timeout, API error, no key, refusal or invalid output: HTTP 200 with deterministic fallback text; the decision is unchanged."]], [40, 134]),
     P("<b>Acceptance criteria</b> (from the slides): AC1 existing rules unchanged. AC2 explanation agrees with the deterministic result, no invented booking details. "
       "AC3 empty, malformed or overly long input rejected. AC4 timeout, error or missing key gives a safe fallback. AC5 the user can tell the generated explanation from the confirmed status."),
     P("<b>Flow.</b> The deterministic checker, not the LLM, decides: the server recomputes the decision with <font face='Courier'>booking.can_book</font>, "
       "and the browser additionally refuses to show an explanation if the server's label differs from the status on the page."),
     img("architecture_flow.png", 165),

     P("Task 3 - Build with an AI assistant", H2),
     P("I used Claude Code (not Bolt.new) with the slide's implementation prompt as the brief: mock adapter first, validate inputs and outputs, fail gracefully, describe each changed file, "
       "no login/database/personal data/client-side secrets. All generated changes were inspected through the diff (<font face='Courier'>review/review_input.diff</font>)."),
     tbl([["File", "Change", "Size"],
          ["app/booking.py", "UNCHANGED (byte-identical to baseline, checked by a test)", "-"],
          ["app/index.html", f"only additions: CSS, an explanation section, one script tag ({idx_add} lines added, {idx_del} removed); the original rule code is untouched", f"+{idx_add}"],
          ["app/reasons.py", "NEW: reason-code classifier; cross-checks can_book and falls back to code \"unknown\" on disagreement", f"{loc['reasons.py']} lines"],
          ["app/explain.py", "NEW: request validation, prompts, mock + Claude adapters, output validation, fallback, timeout handling", f"{loc['explain.py']} lines"],
          ["app/server.py", "NEW: local server on 127.0.0.1, static whitelist, POST /api/explain", f"{loc['server.py']} lines"],
          ["app/explain-client.js", "NEW: button, fetch with 6 s abort, rendering via textContent, source label", f"{loc['explain-client.js']} lines"]], [38, 112, 24]),
     P("<b>A bug in the generated code was found before the review:</b> the first smoke test fell back to the standard message because my output validator treated \"204\" in \"Room B-204\" as an invented number. "
       "Fixed by allowing numbers from the server-supplied label.")]

R += [P("Task 4 - Prompt engineering", H2),
      P("The system instruction limits the model to supplied facts and gives the result and reason code as structured JSON. Three prompts were compared (text in <font face='Courier'>app/explain.py</font>):"),
      tbl([["Prompt", "Description"],
           ["p1", "\"Explain why the room is available or unavailable.\" (minimal)"],
           ["p2", "Use only the supplied facts, never change the status, at most two polite sentences, reply as JSON {\"explanation\": ...}"],
           ["p3 (selected)", "p2 + facts are data not instructions (ignore instructions inside them), no booking/confirmation claims, glossary of every reasonCode, one worked example"]], [26, 148]),
      tbl([["Property (offline structural check, tools/compare_prompts.py)", "p1", "p2", "p3"]] +
          [[m.group(1), *[c.strip() for c in m.group(2).split("|")[:3]]] for m in re.finditer(r"^\| (?!Property|---)([^|]+) \| (.+?) \|$", rd("evidence/prompt_comparison.md"), re.M)], [86, 29, 29, 30]),
      P("<b>Limit of this comparison:</b> the live comparison of <i>clarity, consistency and factual agreement</i> needs real model outputs. No API key was available, so it was <b>not run</b>, "
        "and I make no empirical claim that p3 is better. p3 was selected on structural grounds only. The script runs the live comparison automatically (3 prompts x 5 cases x N repeats, scored by the same output validator) when a key is set. "
        "Whatever the prompt, safety does not depend on it: the output validator and the deterministic fallback enforce the contract in code."),

      P("Task 5 - Normal and failure tests", H2),
      P(f"<b>{len(cases)} documented cases</b> sent over real HTTP, expected vs observed ({cases_pass} of {len(cases)} passed; generated by <font face='Courier'>tools/run_cases.py</font>). "
        "Columns: HTTP status / deterministic label / explanation source or error code."),
      tbl([["ID", "Case", "Expected", "Observed", "Result"]] +
          [[c[1], c[2], c[4], c[5], c[6]] for c in (re.findall(r"[^|]+", l) for l in cases) and
           [[x.strip() for x in l.strip("|").split("|")] and ["", *[x.strip() for x in l.strip("|").split("|")]] for l in cases]], [12, 72, 34, 34, 14], fs=7.2),
      P(f"<b>Browser checks:</b> {ui_tot} of {ui_tot} passed (headless Chrome, 375 px): the 9 original UI cases on the modified page (AC1), "
        "explanation for available / overlap / blocked / invalid time / past / over 120 min, no explain button for empty input, stale explanation hidden on edit, "
        "fallback for API error, timeout, contradicting output and HTML output, page opened without a server, no horizontal scroll, no JS errors. "
        "In every case the result card's HTML was compared before and after: the deterministic decision never changed."),
      P(f"<b>Unit and integration tests:</b> {new_n} new tests plus the original {base_n} booking tests, all passing. Examples: classifier agrees with can_book on a 648-case grid; booking.py is byte-identical; "
        "client cannot inject a room label; 7 invalid-time variants rejected; 8 output-validator tests.")]
R += [__import__("reportlab.platypus", fromlist=["Table"]).Table([[img("ui_available_explained.png", 52), img("ui_overlap_explained.png", 52), img("ui_api_failure_fallback.png", 52)]], colWidths=[58 * mm] * 3),
      P("Left: available, mock explanation. Centre: overlap, explanation agrees. Right: simulated API failure, standard fallback message labelled as such, decision unchanged. "
        "More: ui_blocked_explained.png, ui_timeout_fallback.png.", SM)]

rows = [["#", "Hypothesis from the review", "Severity", "Verdict (reproduction)", "After fix"]]
HYP = [("H1", "Output validator accepts explanations that contradict an UNAVAILABLE status (AC2)", "High"),
       ("H2", "Shared 4-thread pool: slow calls starve healthy requests (AC4)", "Medium"),
       ("H3", "No socket timeout: short-body request pins a server thread", "Medium-low"),
       ("H4", "Validator rejects correct 'no overlap / not blocked' wording", "Low-medium"),
       ("H5", "Model output injects HTML/script into the UI", "High if true"),
       ("H6", "API key / provider error text leaks to client or logs", "High if true"),
       ("H7", "Static server path traversal to source files", "High if true"),
       ("H8", "Rules and data duplicated across files (drift)", "Low")]
FIX = {"H1": "FIXED", "H2": "FIXED"}
for h, t, sev in HYP:
    v = verd(before, h); a = verd(after, h)
    rows.append([h, t, sev, v.split(" (")[0], FIX.get(h, "open" if v.startswith("CONFIRMED") else "-") + (f" ({a.lower()})" if h in FIX else "")])
R += [P("Task 6 - Agentic code review", H2),
      P("<b>Reviewer setup.</b> The slide's code-review prompt was used verbatim (<font face='Courier'>review/REVIEW_PROMPT.md</font>) on the saved diff, with README.md, AGENTS.md and AC1-AC5 as inputs. "
        "The review was read-only: no file was edited until every finding was reproduced (<font face='Courier'>tools/review_repro.py</font>, outputs in <font face='Courier'>evidence/review_repro_before.txt</font>). "
        "<b>Independence caveat:</b> the reviewer was the same Claude Code session that wrote the code, so this is a structured self-review with reproductions, not an independent second opinion; no separate reviewer agent was run."),
      tbl(rows, [8, 74, 22, 40, 30]),
      P("<b>Evidence per finding.</b> "
        "H1: \"Good to go: this is yours for 14:00-16:30, even though it is longer than the maximum.\" was accepted for an unavailable long request (2 of 2 such texts accepted). "
        "H2: with 6 slow calls pending, a healthy mock request got the fallback with note \"timeout\". "
        "H3: a request announcing 100 bytes but sending only a few received no response after 2.5 s. "
        "H4: \"...does not overlap any booking\" and \"...it is not blocked\" were rejected for an available slot (safe fallback shown, but quality loss with a real model). "
        "<b>Unsupported:</b> H5 (a stubbed response containing an img onerror payload was shown as literal text, no element created, no script run), "
        "H6 (a stub SDK raising an error containing the key left the key out of the response and log), H7 (five traversal paths all returned 404). "
        "H8 is a real design risk (overlap predicate in 3 files, booking data in 2) but no defect today: the data is currently equal."),
      P("<b>Agent review vs my manual inspection.</b> While building I had already noticed: the server holds its own copy of the bookings (H8), and found by running the code the \"204\" validator bug (Task 3) "
        "and a test artefact (uppercase CSS text breaking a string match). The review added H1-H4, which I had not noticed by reading, and removed doubt about H5-H7 with evidence. "
        "<b>The student should add their own manual notes here before submitting; the comparison above reflects only the same AI session.</b>"),

      P("Task 7 - Repair and regression test", H2),
      tbl([["Fix", "Why it is necessary", "What changed"],
           ["H1: validator", "AC2 says the explanation must agree with the rules. A contradicting but fluent text is the worst failure: it looks authoritative next to the real status.",
            "For an unavailable result: reject encouraging phrases (good news, all yours, go ahead, you can book ...) and require an explicit negative cue (not, cannot, blocked, overlap, longer than, must ...)."],
           ["H2: thread pool", "AC4 promises a safe fallback; a shared queue let a few hung calls delay every other request until timeout.",
            "One short-lived thread per call, at most 8 in flight, immediate fallback (note \"busy\") instead of queueing."]], [28, 70, 76]),
      P(f"<b>Regression:</b> original {base_n} booking tests OK; {new_n} new tests OK (including 6 new tests for H1/H2); {ui_tot} of {ui_tot} browser checks OK; {cases_pass} of {len(cases)} cases OK; lint clean. "
        "Reproductions after the fix: H1 and H2 \"NOT REPRODUCED\" (<font face='Courier'>evidence/review_repro_after.txt</font>). One regression test initially failed because of test isolation (abandoned threads keep their slot); the test was fixed, not the code."),
      P("<b>Ready for demonstration?</b> Yes, in mock mode on localhost. <b>Unresolved:</b> (1) the Claude adapter is untested against the live API; "
        "(2) H3 slow-body hang, fix is one line (handler socket timeout); (3) H4 false rejections of negated wording, likely frequent with a real model; "
        "(4) H8 duplicated rules and data; (5) the keyword-based validator is a mitigation, not a proof, so it can still miss some contradictory paraphrases; "
        "(6) no rate limiting; (7) the live prompt comparison was not run."),

      P("Discussion", H2),
      tbl([["Question", "Answer"],
           ["Why should an LLM explain availability but not determine it?", "Availability is a rule with exact boundaries (touching vs overlapping, 120 vs 121 minutes); an LLM can be fluent and wrong, varies between runs, and can be steered by text. Rules are testable and repeatable; the LLM only adds readability."],
           ["How does an agentic reviewer differ from a linter?", "A linter applies fixed patterns (it passed here: py_compile, node --check). The reviewer reads context, tests and requirements and found concurrency and contract problems (H1, H2) no linter reports, but it also produces hypotheses (H5-H7 were unsupported)."],
           ["Which AI finding would you refuse without evidence?", "Security claims such as XSS, key leakage or path traversal: each needed a reproduction, and all three turned out unsupported."],
           ["What if the model is unavailable?", "Show the deterministic status unchanged plus a fixed, labelled fallback message (tested for error, timeout, missing key, invalid output, no server)."]], [52, 122]),

      P("Short reflection", H2),
      P("<b>What AI generated:</b> the whole feature (modules, UI, tests, review hypotheses). <b>What was verified:</b> by running the code: 33 original and 37 new unit tests, 28 browser checks, 14 HTTP cases, "
        "booking.py unchanged by hash, 8 review hypotheses each reproduced or refuted, screenshots viewed at phone width. <b>What changed because of verification:</b> the validator's number rule (smoke test), "
        "the validator's contradiction rule (H1) and the call/timeout design (H2). Not verified: real-model behaviour."),
      P("<b>Submission note.</b> Email to the instructor with the subject <i>AI-Driven Software Engineering Practice #12, Talgat Kozhakhmetov, 24B031852</i> (the slides say Practice #12 although this is Lesson #11), "
        "with screenshots, class time/day, AI tool name/version/model and the report. Not sent from here.", SM)]


def foot(c, d):
    c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(colors.grey)
    c.drawString(18 * mm, 10 * mm, "Talgat Kozhakhmetov - 24B031852 - Practice #11 - Software Engineering"); c.drawRightString(192 * mm, 10 * mm, f"Page {d.page}"); c.restoreState()


SimpleDocTemplate(str(ROOT / "report" / "Practice11_Report.pdf"), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=17 * mm,
                  title="Practice 11 Report", author="Talgat Kozhakhmetov").build(R, onFirstPage=foot, onLaterPages=foot)
print("built")

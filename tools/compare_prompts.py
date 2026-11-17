"""Compares the three system prompts (p1 minimal, p2 constrained, p3 constrained + injection guard + reason glossary + example).
Offline part (always runs): structural properties of each prompt - clarity features, size. NO model output is involved.
Live part (only with ANTHROPIC_API_KEY + `pip install anthropic`): every prompt x 5 fact cases x N repeats is sent to the model;
factual agreement = output passes explain.validate_output, consistency = number of distinct outputs per case.
Run: python3 -I tools/compare_prompts.py [repeats]"""
import json, os, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import explain as ex

FEATURES = {
    "limits model to supplied facts": lambda t: "only the facts" in t.lower(),
    "forbids changing the status": lambda t: "never change" in t.lower(),
    "length limit (<= 2 sentences)": lambda t: "two" in t.lower() and "sentence" in t.lower(),
    "demands JSON output shape": lambda t: '{"explanation"' in t,
    "treats input as data (injection guard)": lambda t: "ignore any instruction" in t.lower(),
    "forbids booking/confirmation claims": lambda t: "confirmed" in t.lower(),
    "defines every reasonCode": lambda t: all(c in t for c in ("blocked=", "range=", "past=", "long=", "overlap=")),
    "contains a worked example": lambda t: "Example:" in t,
}
CASES = [("ok", True, "12:00", "13:00"), ("overlap", False, "10:30", "11:30"), ("blocked", False, "12:00", "13:00"),
         ("past", False, "08:00", "09:00"), ("long", False, "14:00", "16:30")]
out = ["# Prompt comparison", "", "## Offline structural comparison (no model involved)", "",
       "| Property | p1 minimal | p2 constrained | p3 constrained + guard |", "|---|---|---|---|"]
for name, fn in FEATURES.items():
    out.append(f"| {name} | " + " | ".join("yes" if fn(ex.PROMPTS[p]) else "no" for p in ("p1", "p2", "p3")) + " |")
out.append("| characters (tokens ~ chars/4, estimate) | " + " | ".join(f"{len(ex.PROMPTS[p])} (~{len(ex.PROMPTS[p])//4})" for p in ("p1", "p2", "p3")) + " |")
out.append("| features satisfied (of %d) | " % len(FEATURES) + " | ".join(str(sum(fn(ex.PROMPTS[p]) for fn in FEATURES.values())) for p in ("p1", "p2", "p3")) + " |")

key = os.environ.get("ANTHROPIC_API_KEY")
try:
    import anthropic  # noqa: F401
    sdk = True
except ImportError:
    sdk = False
out += ["", "## Live comparison (factual agreement and consistency)", ""]
if not (key and sdk):
    out.append("**NOT RUN** - " + ("ANTHROPIC_API_KEY is not set" if not key else "the anthropic SDK is not installed") +
               ". No model outputs exist for these prompts, so no claim about factual agreement or consistency is made. "
               "To run: `pip install anthropic; export ANTHROPIC_API_KEY=...; python3 -I tools/compare_prompts.py 3`.")
else:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    ad = ex.AnthropicAdapter(timeout=30)
    out += ["| Prompt | valid & consistent with status | distinct outputs per case (avg) |", "|---|---|---|"]
    for p in ("p1", "p2", "p3"):
        good = total = distinct = 0
        for code, ok, s, e in CASES:
            f = {"roomLabel": ex.ROOM_LABEL, "start": s, "end": e, "isAvailable": ok, "reasonCode": code}
            seen = set()
            for _ in range(n):
                total += 1
                try:
                    txt = ad.complete(*ex.build_messages(p, f)); seen.add(txt.strip())
                    ex.validate_output(json.loads(txt), f); good += 1
                except Exception:
                    pass
            distinct += len(seen)
        out.append(f"| {p} | {good}/{total} | {distinct/len(CASES):.1f} |")
text = "\n".join(out) + "\n"
(ROOT / "evidence" / "prompt_comparison.md").write_text(text); print(text)

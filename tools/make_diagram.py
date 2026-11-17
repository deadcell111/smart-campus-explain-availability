"""Draws the request -> rule engine -> LLM adapter -> response flow. Run: python3 tools/make_diagram.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path
OUT = Path(__file__).resolve().parent.parent / "shots" / "architecture_flow.png"
fig, ax = plt.subplots(figsize=(10, 5.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 5.8); ax.axis("off")

def box(x, y, w, h, t, sub="", fc="#eef2fb", ec="#1f4fd8"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.5))
    ax.text(x + w / 2, y + h - 0.14, t, ha="center", va="top", fontsize=9, weight="bold")
    ax.text(x + w / 2, y + h - 0.45, sub, ha="center", va="top", fontsize=7.2, color="#33415c", linespacing=1.3)

def arr(a, b, label="", color="#444", ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, color=color, lw=1.3, linestyle=ls))
    if label: ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.12, label, fontsize=7, ha="center", color=color)

ax.axvline(3.45, ymin=0.02, ymax=0.93, color="#a3171d", ls="--", lw=1.2)
ax.text(3.5, 5.3, "trust boundary: browser | server", fontsize=7.5, color="#a3171d")
# top row: request path
box(0.1, 3.7, 3.1, 1.3, "Browser (index.html)", "student enters times; original checker\nshows Available / Unavailable;\n[Explain availability] button", "#fdf3e7", "#c77700")
box(3.8, 3.7, 2.7, 1.3, "1. Validate request", "<=512 B, exact keys, HH:MM, bool\nelse HTTP 400 / 413 (AC3)", "#fff8e1", "#8a5a00")
box(7.1, 3.7, 2.8, 1.3, "2. Rule engine (authoritative)", "booking.can_book() + reason code\nLLM never sees booking data", "#e9f7ee", "#116b3a")
# bottom row: explanation path (right to left)
box(7.1, 0.2, 2.8, 1.3, "3. Adapter (server-side)", "mock (default) or Claude; key only in\nserver env; 3 s timeout; in-flight cap", "#eef2fb", "#1f4fd8")
box(3.8, 0.2, 2.7, 1.3, "4. Validate model output", "JSON {explanation}, <=280 chars,\n<=2 sentences, only supplied times,\nno markup, agrees with status", "#fff8e1", "#8a5a00")
box(0.1, 0.2, 3.1, 1.3, "Explanation box (browser)", "dashed border, 'AI-generated explanation',\nsource label, 'not a booking confirmation';\nrendered with textContent", "#f3f6ff", "#1f4fd8")
box(3.8, 2.1, 2.7, 1.0, "Deterministic fallback", "fixed text per reason code (AC4)", "#fdeaea", "#a3171d")
arr((3.2, 4.35), (3.8, 4.35)); ax.text(3.5, 4.5, "POST", fontsize=7, ha="center")
arr((6.5, 4.35), (7.1, 4.35)); arr((8.5, 3.7), (8.5, 1.5), "facts only: room, times,\nisAvailable, reasonCode")
arr((7.1, 0.85), (6.5, 0.85), "text"); arr((3.8, 0.85), (3.2, 0.85), "ok")
arr((5.15, 1.5), (5.15, 2.1), "reject / timeout / error / no key", "#a3171d", ":"); arr((3.8, 2.4), (1.9, 1.5), "fallback text", "#a3171d", ":")
ax.text(5.0, 5.55, "Request -> rule engine -> LLM adapter -> response", ha="center", fontsize=11, weight="bold")
fig.tight_layout(); fig.savefig(OUT, dpi=170); print("ok")

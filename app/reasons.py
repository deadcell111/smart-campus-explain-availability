"""Deterministic decision + reason code for the explain feature.

can_book() in booking.py stays the ONLY source of truth for availability (unchanged, AC1).
reason_code() only classifies WHY a request was rejected, in the same order as the rules.
decide() cross-checks the two and degrades to reasonCode "unknown" if they ever disagree.
"""
from booking import can_book

NOW = 540                                     # 09:00, fixed (same as index.html)
ROOM_LABEL = "Room B-204"                     # fixed server-side; never taken from the client
EXISTING = ((600, 660), (780, 870))           # fictional bookings (same as index.html)
REASONS = ("ok", "blocked", "range", "past", "long", "overlap", "unknown")


def reason_code(start, end, now, blocked, existing):
    if blocked:
        return "blocked"
    if not (0 <= start < end <= 1440):
        return "range"
    if start <= now:
        return "past"
    if end - start > 120:
        return "long"
    for b_start, b_end in existing:
        if start < b_end and b_start < end:
            return "overlap"
    return "ok"


def decide(start, end, blocked, now=NOW, existing=EXISTING):
    ok = can_book(start, end, now, blocked, existing)
    code = reason_code(start, end, now, blocked, existing)
    if ok != (code == "ok"):                  # classifier disagrees with the authoritative rule
        code = "unknown"
    return ok, ("ok" if ok else code)

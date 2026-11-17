"""Smart Campus Room Availability Checker - booking rules (final version)."""

MAX_DURATION = 120
MINUTES_PER_DAY = 1440


def _is_minute(value):
    """True for a real int (bool is rejected although it subclasses int)."""
    return isinstance(value, int) and not isinstance(value, bool)


def can_book(start, end, now, blocked, existing):
    """Return True only if [start, end) is a valid, free request.

    start, end, now: integer minutes after midnight.
    blocked: True if the selected room is blocked.
    existing: iterable of (start, end) bookings. It is only read, never changed.
    """
    # AC3: a blocked room rejects every request.
    if blocked:
        return False
    # Defensive: non-integer minutes cannot be valid requests.
    if not (_is_minute(start) and _is_minute(end)):
        return False
    # AC1: 0 <= start < end <= 1440, and start strictly after now.
    if not (0 <= start < end <= MINUTES_PER_DAY):
        return False
    if start <= now:
        return False
    # AC2: at most 120 minutes (exactly 120 is allowed).
    if end - start > MAX_DURATION:
        return False
    # AC4: reject overlap; touching endpoints (start == b_end) do not overlap.
    for b_start, b_end in existing:
        if start < b_end and b_start < end:
            return False
    return True

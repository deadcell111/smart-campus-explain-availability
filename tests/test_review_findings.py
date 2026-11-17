"""Regression tests for the two confirmed review findings that were fixed (H1, H2)."""
import threading
import time
import unittest

import _path  # noqa: F401
import explain as ex


def facts(code, ok, s="12:00", e="13:00"):
    return {"roomLabel": "Room B-204", "start": s, "end": e, "isAvailable": ok, "reasonCode": code}


class TestH1ValidatorContradictions(unittest.TestCase):
    def rejects(self, text, f):
        with self.assertRaises(ex.OutputRejected):
            ex.validate_output({"explanation": text}, f)

    def test_encouraging_text_for_long_request_rejected(self):
        self.rejects("Good to go: this is yours for 14:00-16:30, even though it is longer than the maximum.", facts("long", False, "14:00", "16:30"))

    def test_encouraging_text_for_overlap_rejected(self):
        self.rejects("No problem, the room is all yours at 10:30-11:30, it already has other bookings.", facts("overlap", False, "10:30", "11:30"))

    def test_unavailable_text_without_negative_cue_rejected(self):
        self.rejects("The room has some existing bookings today.", facts("overlap", False))

    def test_correct_unavailable_explanations_still_accepted(self):
        self.assertTrue(ex.validate_output({"explanation": "This overlaps an existing booking, so it is not available. Please pick another time."}, facts("overlap", False)))
        self.assertTrue(ex.validate_output({"explanation": "The request is longer than the 120-minute maximum. Please shorten it."}, facts("long", False)))


class TestH2NoStarvation(unittest.TestCase):
    def setUp(self):
        self.drain()
        self.addCleanup(self.drain)

    @staticmethod
    def drain():
        """Abandoned (timed-out) worker threads keep their in-flight slot until they finish; wait for all 8 to be free."""
        deadline = time.time() + 5
        while ex._INFLIGHT._value < 8 and time.time() < deadline:
            time.sleep(0.05)

    def test_healthy_request_not_blocked_by_slow_ones(self):
        class Slow:
            source = "mock"

            def complete(self, s, u):
                time.sleep(1.2)
                return "{}"
        body = b'{"start":"12:00","end":"13:00","blocked":false}'
        ts = [threading.Thread(target=lambda: ex.explain(body, Slow(), timeout=0.1)) for _ in range(6)]
        for t in ts:
            t.start()
        time.sleep(0.2)
        r = ex.explain(body, ex.MockAdapter("ok"), timeout=0.5)
        for t in ts:
            t.join()
        self.assertEqual(r["explanation"]["source"], "mock")

    def test_cap_reached_fails_fast_with_fallback(self):
        class Slow:
            source = "mock"

            def complete(self, s, u):
                time.sleep(1.0)
                return "{}"
        body = b'{"start":"12:00","end":"13:00","blocked":false}'
        ts = [threading.Thread(target=lambda: ex.explain(body, Slow(), timeout=0.05)) for _ in range(8)]
        for t in ts:
            t.start()
        time.sleep(0.2)
        t0 = time.time()
        r = ex.explain(body, ex.MockAdapter("ok"), timeout=2)
        elapsed = time.time() - t0
        for t in ts:
            t.join()
        self.assertEqual((r["explanation"]["source"], r["explanation"]["note"]), ("fallback", "adapter_error: busy"))
        self.assertLess(elapsed, 0.5)               # answered immediately instead of queueing
        self.assertTrue(r["decision"]["isAvailable"])


if __name__ == "__main__":
    unittest.main()

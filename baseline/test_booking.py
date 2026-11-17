"""Acceptance tests for can_book (AC1-AC5). Run: python3 test_booking.py -v"""
import copy
import importlib
import os
import unittest

# Choose the implementation under test: BOOKING_MODULE=booking_v1 to test v1.
booking = importlib.import_module(os.environ.get("BOOKING_MODULE", "booking"))
can_book = booking.can_book

NOW = 540
EXISTING = [(600, 660)]


class TestBaseCases(unittest.TestCase):
    def test_free_slot_available(self):
        self.assertTrue(can_book(700, 760, NOW, False, EXISTING))

    def test_touching_end_of_booking_available(self):          # AC4
        self.assertTrue(can_book(660, 720, NOW, False, EXISTING))

    def test_touching_start_of_booking_available(self):        # AC4
        self.assertTrue(can_book(540 + 1, 600, NOW, False, EXISTING))

    def test_overlap_partial_unavailable(self):                # AC4
        self.assertFalse(can_book(630, 690, NOW, False, EXISTING))

    def test_overlap_start_inside_unavailable(self):           # AC4
        self.assertFalse(can_book(570, 630, NOW, False, EXISTING))

    def test_overlap_contained_unavailable(self):              # AC4
        self.assertFalse(can_book(610, 650, NOW, False, EXISTING))

    def test_overlap_containing_unavailable(self):             # AC4
        self.assertFalse(can_book(590, 670, NOW, False, EXISTING))

    def test_blocked_unavailable(self):                        # AC3
        self.assertFalse(can_book(660, 720, NOW, True, EXISTING))

    def test_blocked_rejects_even_otherwise_valid(self):       # AC3
        self.assertFalse(can_book(700, 760, NOW, True, []))

    def test_exactly_120_minutes_available(self):              # AC2
        self.assertTrue(can_book(720, 840, NOW, False, EXISTING))

    def test_121_minutes_unavailable(self):                    # AC2
        self.assertFalse(can_book(720, 841, NOW, False, EXISTING))

    def test_starts_now_unavailable(self):                     # AC1
        self.assertFalse(can_book(540, 570, NOW, False, EXISTING))

    def test_starts_before_now_unavailable(self):              # AC1
        self.assertFalse(can_book(500, 560, NOW, False, EXISTING))

    def test_starts_one_minute_after_now_available(self):      # AC1
        self.assertTrue(can_book(541, 570, NOW, False, []))


class TestBounds(unittest.TestCase):
    def test_reversed_times_unavailable(self):                 # AC1
        self.assertFalse(can_book(700, 650, NOW, False, []))

    def test_zero_length_unavailable(self):                    # AC1
        self.assertFalse(can_book(700, 700, NOW, False, []))

    def test_negative_start_unavailable(self):                 # AC1
        self.assertFalse(can_book(-1, 30, NOW, False, []))

    def test_end_beyond_midnight_unavailable(self):            # AC1
        self.assertFalse(can_book(1400, 1441, NOW, False, []))

    def test_end_exactly_1440_available(self):                 # AC1
        self.assertTrue(can_book(1380, 1440, NOW, False, []))

    def test_start_1440_unavailable(self):                     # AC1
        self.assertFalse(can_book(1440, 1441, NOW, False, []))

    def test_start_zero_with_now_zero_unavailable(self):       # AC1
        self.assertFalse(can_book(0, 30, 0, False, []))

    def test_start_zero_with_now_zero_before_start(self):
        self.assertTrue(can_book(1, 30, 0, False, []))

    def test_now_last_minute_nothing_bookable(self):           # now=1439
        self.assertFalse(can_book(1439, 1440, 1439, False, []))


class TestMultipleAndPurity(unittest.TestCase):
    def test_multiple_bookings_gap_available(self):
        ex = [(600, 660), (720, 780), (900, 960)]
        self.assertTrue(can_book(660, 720, NOW, False, ex))

    def test_multiple_bookings_later_one_overlaps(self):
        ex = [(600, 660), (720, 780), (900, 960)]
        self.assertFalse(can_book(740, 800, NOW, False, ex))

    def test_empty_existing_available(self):
        self.assertTrue(can_book(700, 760, NOW, False, []))

    def test_existing_unsorted(self):
        ex = [(900, 960), (600, 660)]
        self.assertFalse(can_book(630, 690, NOW, False, ex))

    def test_inputs_not_mutated(self):                         # AC5
        ex = [(900, 960), (600, 660), (720, 780)]
        before = copy.deepcopy(ex)
        can_book(630, 690, NOW, False, ex)
        can_book(1000, 1060, NOW, False, ex)
        self.assertEqual(ex, before)

    def test_returns_real_bool(self):
        self.assertIs(can_book(700, 760, NOW, False, []), True)
        self.assertIs(can_book(630, 690, NOW, False, EXISTING), False)
        self.assertIs(can_book(700, 760, NOW, True, []), False)


class TestInputTypeRobustness(unittest.TestCase):
    """Cleanup-driven checks (not in AC1-AC6 text): non-integer minutes."""

    def test_float_minutes_rejected(self):
        self.assertFalse(can_book(700.5, 760, NOW, False, []))

    def test_bool_minutes_rejected(self):
        self.assertFalse(can_book(True, 30, 0, False, []))

    def test_none_rejected(self):
        self.assertFalse(can_book(None, 760, NOW, False, []))

    def test_string_rejected(self):
        self.assertFalse(can_book("700", 760, NOW, False, []))


if __name__ == "__main__":
    unittest.main()

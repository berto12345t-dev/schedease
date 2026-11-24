"""Executable verification suite for SchedEase's proposal requirements."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from schedule_models import Meeting, ScheduleState, SchedulingError
from schedule_structures import BinarySearchTree, LinkedQueue
from schedule_validation import validate_meeting
from scheduler import ScheduleEngine


def add_section(engine, code, title, units, section, slots, day, start, end):
    return engine.add_section(code, title, units, section, slots, [(day, start, end)])


def proposal_sample():
    engine = ScheduleEngine(9)
    engine.add_blocked_period("Monday", "07:00", "10:00", "Work")
    add_section(engine, "CPEN65", "Software Design", 3, "2-1", 5, "Tuesday", "09:00", "12:00")
    add_section(engine, "CPEN65", "Software Design", 3, "2-2", 4, "Wednesday", "09:00", "12:00")
    engine.set_pinned("CPEN65", True)
    add_section(engine, "CPEN125", "Digital Systems", 3, "4-1", 12, "Tuesday", "10:00", "13:00")
    add_section(engine, "CPEN125", "Digital Systems", 3, "4-2", 0, "Friday", "09:00", "12:00")
    add_section(engine, "CPEN135", "Computer Architecture", 3, "4-1", 8, "Wednesday", "12:00", "15:00")
    add_section(engine, "CPEN135", "Computer Architecture", 3, "4-2", 6, "Thursday", "08:00", "11:00")
    add_section(engine, "CPEN135", "Computer Architecture", 3, "4-3", 3, "Monday", "08:00", "11:00")
    add_section(engine, "CPEN111", "Engineering Mathematics", 1, "4-1", 10, "Friday", "13:00", "14:00")
    return engine


class QueueTests(unittest.TestCase):
    def test_fifo_peek_empty_and_display(self):
        queue = LinkedQueue()
        self.assertTrue(queue.is_empty())
        queue.enqueue("first")
        queue.enqueue("second")
        self.assertEqual(queue.peek(), "first")
        self.assertEqual(queue.display(), ["first", "second"])
        self.assertEqual(queue.dequeue(), "first")
        self.assertEqual(queue.dequeue(), "second")
        self.assertTrue(queue.is_empty())
        with self.assertRaises(IndexError):
            queue.dequeue()


class BSTTests(unittest.TestCase):
    def test_insert_inorder_predecessor_successor_and_overlap(self):
        tree = BinarySearchTree()
        first = validate_meeting("Tuesday", "09:00", "12:00", "A", "Course A", "1")
        third = validate_meeting("Tuesday", "14:00", "15:00", "C", "Course C", "1")
        tree.insert(first)
        tree.insert(third)
        self.assertEqual([node.subject_code for node in tree.inorder()], ["A", "C"])
        middle = validate_meeting("Tuesday", "12:00", "13:00", "B", "Course B", "1")
        self.assertEqual(tree.find_predecessor(middle.key).subject_code, "A")
        self.assertEqual(tree.find_successor(middle.key).subject_code, "C")
        self.assertIsNone(tree.find_overlap(middle))
        overlapping = validate_meeting("Tuesday", "11:00", "12:30", "D", "Course D", "1")
        self.assertEqual(tree.find_overlap(overlapping).subject_code, "A")

    def test_deep_copy_isolated_and_back_to_back_allowed(self):
        tree = BinarySearchTree()
        tree.insert(validate_meeting("Wednesday", "09:00", "12:00", "A", "Course A", "1"))
        copy = tree.deep_copy()
        copy.insert(validate_meeting("Wednesday", "12:00", "13:00", "B", "Course B", "1"))
        self.assertEqual(tree.size, 1)
        self.assertEqual(copy.size, 2)


class ValidationTests(unittest.TestCase):
    def test_invalid_maximum_units_is_controlled(self):
        for value in (0, "not-a-number", "2.5"):
            with self.subTest(value=value):
                with self.assertRaises(SchedulingError):
                    ScheduleEngine(value)

    def test_normal_subject_and_multiple_sections(self):
        engine = ScheduleEngine(9)
        add_section(engine, "CPEN65", "Software Design", 3, "2-1", 5, "Tuesday", "09:00", "12:00")
        add_section(engine, "CPEN65", "Software Design", 3, "2-2", 4, "Wednesday", "09:00", "12:00")
        self.assertEqual(len(engine.subjects["CPEN65"].sections), 2)

    def test_missing_tba_invalid_times_and_days(self):
        for day, start, end in [
            ("Monday", "TBA", "12:00"),
            ("Monday", "10:00", "09:00"),
            ("Monday", "10:00", "10:00"),
            ("Sunday", "10:00", "11:00"),
            ("Monday", "06:59", "08:00"),
            ("Monday", "20:00", "21:01"),
        ]:
            with self.subTest(day=day, start=start, end=end):
                with self.assertRaises(SchedulingError):
                    validate_meeting(day, start, end, "A", "Title", "1")

    def test_duplicate_subject_section_and_negative_slots(self):
        engine = ScheduleEngine(9)
        add_section(engine, "CPEN65", "Software Design", 3, "2-1", 5, "Tuesday", "09:00", "12:00")
        with self.assertRaisesRegex(SchedulingError, "already exists"):
            add_section(engine, "CPEN65", "Software Design", 3, "2-1", 4, "Wednesday", "09:00", "12:00")
        with self.assertRaisesRegex(SchedulingError, "negative"):
            add_section(engine, "CPEN70", "Networks", 3, "1", -1, "Thursday", "09:00", "10:00")

    def test_section_meetings_may_not_overlap(self):
        engine = ScheduleEngine(9)
        with self.assertRaisesRegex(SchedulingError, "overlap"):
            engine.add_section(
                "CPEN65", "Software Design", 3, "2-1", 5,
                [("Tuesday", "09:00", "12:00"), ("Tuesday", "11:30", "13:00")],
            )

    def test_zero_slots_optional_and_pinned(self):
        engine = ScheduleEngine(3)
        add_section(engine, "CPEN65", "Software Design", 3, "FULL", 0, "Tuesday", "09:00", "12:00")
        result = engine.generate()
        self.assertIsNone(result.error)
        self.assertEqual(result.recommendations[0].state.units, 0)
        engine.set_pinned("CPEN65", True)
        self.assertIn("no section with available slots", engine.generate().error)

    def test_blocked_time_and_conflict_report(self):
        engine = ScheduleEngine(3)
        engine.add_blocked_period("Monday", "07:00", "10:00", "Work")
        with self.assertRaisesRegex(SchedulingError, "overlaps existing blocked time"):
            engine.add_blocked_period("Monday", "09:00", "11:00", "Appointment")
        add_section(engine, "CPEN65", "Software Design", 3, "1", 2, "Monday", "08:00", "11:00")
        engine.set_pinned("CPEN65", True)
        message = engine.generate().error
        self.assertIn("CPEN65", message)
        self.assertIn("blocked period 'Work'", message)


class GenerationTests(unittest.TestCase):
    def test_proposal_sample_top_three_ranking(self):
        result = proposal_sample().generate()
        self.assertIsNone(result.error)
        self.assertEqual(len(result.recommendations), 3)
        self.assertEqual(
            [(item.state.units, item.campus_days, item.idle_gap_minutes) for item in result.recommendations],
            [(9, 2, 0), (9, 3, 0), (7, 2, 0)],
        )
        for item in result.recommendations:
            self.assertIn("CPEN65", {code for code, _section in item.state.selected_sections})

    def test_pinned_subjects_never_skipped(self):
        engine = ScheduleEngine(6)
        add_section(engine, "PIN1", "Pinned One", 3, "A", 3, "Monday", "09:00", "10:00")
        add_section(engine, "OPT1", "Optional One", 3, "A", 3, "Tuesday", "09:00", "10:00")
        engine.set_pinned("PIN1", True)
        result = engine.generate()
        self.assertIsNone(result.error)
        self.assertTrue(all("PIN1" in {code for code, _ in item.state.selected_sections} for item in result.recommendations))

    def test_conflicting_pinned_subject_identified(self):
        engine = ScheduleEngine(9)
        add_section(engine, "CPEN65", "Software Design", 3, "2-1", 5, "Tuesday", "09:00", "12:00")
        add_section(engine, "CPEN125", "Digital Systems", 3, "4-1", 12, "Tuesday", "10:00", "13:00")
        engine.set_pinned("CPEN65", True)
        engine.set_pinned("CPEN125", True)
        self.assertIn("Unplaceable pinned subject: CPEN125", engine.generate().error)

    def test_pinned_units_over_cap(self):
        engine = ScheduleEngine(5)
        add_section(engine, "A", "Course A", 3, "1", 1, "Monday", "09:00", "10:00")
        add_section(engine, "B", "Course B", 3, "1", 1, "Tuesday", "09:00", "10:00")
        engine.set_pinned("A", True)
        engine.set_pinned("B", True)
        self.assertIn("exceeding the 5-unit maximum", engine.generate().error)

    def test_unit_cap_boundary(self):
        engine = ScheduleEngine(9)
        add_section(engine, "A", "Course A", 9, "1", 1, "Monday", "09:00", "10:00")
        result = engine.generate()
        self.assertEqual(result.recommendations[0].state.units, 9)

    def test_empty_subject_data(self):
        result = ScheduleEngine(9).generate()
        self.assertIn("No course data has been entered yet", result.error)

    def test_blocked_period_excluded_from_days_and_output_tree_scoring(self):
        engine = ScheduleEngine(3)
        engine.add_blocked_period("Monday", "07:00", "10:00", "Work")
        add_section(engine, "A", "Course A", 3, "1", 1, "Tuesday", "09:00", "10:00")
        result = engine.generate()
        self.assertEqual(result.recommendations[0].campus_days, 1)

    def test_high_combination_workload(self):
        engine = ScheduleEngine(8)
        for index in range(8):
            start_hour = 7 + index
            start = f"{start_hour:02d}:00"
            end = f"{start_hour:02d}:30"
            code = f"C{index + 1}"
            for suffix, slots in (("A", 2), ("B", 2), ("FULL", 0)):
                add_section(engine, code, f"Course {index + 1}", 1, suffix, slots, "Monday", start, end)
        result = engine.generate()
        self.assertIsNone(result.error)
        self.assertEqual(len(result.recommendations), 3)
        self.assertGreater(result.states_processed, 1000)
        self.assertTrue(all(item.state.units == 8 for item in result.recommendations))

    def test_bfs_state_trees_are_independent(self):
        engine = ScheduleEngine(6)
        add_section(engine, "A", "Course A", 3, "1", 1, "Monday", "09:00", "10:00")
        add_section(engine, "B", "Course B", 3, "1", 1, "Tuesday", "09:00", "10:00")
        result = engine.generate()
        self.assertIsNone(result.error)
        # The result tree is not the base BST and contains only the selected schedule meetings.
        self.assertIsNot(result.recommendations[0].state.tree, engine.base_tree)
        self.assertEqual(engine.base_tree.size, 0)
        self.assertEqual(result.recommendations[0].state.tree.size, 2)


if __name__ == "__main__":
    unittest.main()

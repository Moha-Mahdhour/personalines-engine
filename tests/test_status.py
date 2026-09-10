import unittest

from personalines.status import (
    InvalidTransition, TaskStatus, can_transition, check_transition,
)


class StatusTests(unittest.TestCase):
    def test_happy_path_is_allowed(self):
        path = [TaskStatus.INIT, TaskStatus.SEARCHING, TaskStatus.PERSONALIZING, TaskStatus.COMPLETED]
        for a, b in zip(path, path[1:]):
            self.assertTrue(can_transition(a, b), f"{a} -> {b}")

    def test_any_active_state_can_fail(self):
        for s in (TaskStatus.INIT, TaskStatus.SEARCHING, TaskStatus.PERSONALIZING):
            self.assertTrue(can_transition(s, TaskStatus.ERROR))

    def test_skipping_a_stage_is_rejected(self):
        with self.assertRaises(InvalidTransition):
            check_transition(TaskStatus.INIT, TaskStatus.COMPLETED)

    def test_terminal_states_have_no_exits(self):
        for s in (TaskStatus.COMPLETED, TaskStatus.ERROR):
            self.assertTrue(s.is_terminal)
            for t in TaskStatus:
                self.assertFalse(can_transition(s, t))

    def test_parse_is_case_insensitive_and_strict(self):
        self.assertIs(TaskStatus.parse("personalizing"), TaskStatus.PERSONALIZING)
        self.assertIs(TaskStatus.parse(" Init "), TaskStatus.INIT)
        with self.assertRaises(ValueError):
            TaskStatus.parse("Queued")

    def test_value_round_trips_to_the_stored_string(self):
        self.assertEqual(TaskStatus.SEARCHING.value, "Searching")


if __name__ == "__main__":
    unittest.main()

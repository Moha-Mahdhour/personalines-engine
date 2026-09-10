import random
import tempfile
import threading
import time
import unittest
from pathlib import Path

from personalines.examples import ExampleBank
from personalines.jobs import JobFiles, parse_csv, render_csv
from personalines.llm import LLMError
from personalines.pipeline import PersonalizerStage
from personalines.status import TaskStatus
from personalines.storage import InMemoryTaskStore
from tests.helpers import task

ENRICHED = [
    {"Name": "Jordan", "LinkedIn": "u1", "Description": "Headline: Head of Operations"},
    {"Name": "Riley", "LinkedIn": "u2", "Description": "Headline: Robotics Engineer"},
    {"Name": "Casey", "LinkedIn": "u3", "Description": "Headline: Data Scientist"},
]


class FakeChat:
    """Answers from the headline in the prompt; can fail or stall for chosen leads."""

    def __init__(self, fail_on=(), jitter=False):
        self.fail_on, self.jitter, self.calls, self.lock = set(fail_on), jitter, 0, threading.Lock()

    def complete(self, messages):
        with self.lock:
            self.calls += 1
        prompt = messages[1]["content"]
        headline = prompt.split("Headline: ")[1].splitlines()[0]
        if self.jitter:
            time.sleep(random.random() / 50)
        if headline in self.fail_on:
            raise LLMError("HTTP 500")
        return f'"Great to see your work as {headline}!"'


class PersonalizerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.t = task(status=TaskStatus.PERSONALIZING)
        self.files = JobFiles.for_task(self.t)

    def run_stage(self, chat, rows=ENRICHED):
        store = InMemoryTaskStore({self.files.remote_formatted: render_csv(rows)})
        stage = PersonalizerStage(store, chat, ExampleBank.from_text("a\nb\nc"), Path(self.tmp.name),
                                  max_workers=4, rng=random.Random(0))
        return store, stage.run(self.t)

    def test_writes_lines_in_input_order_and_completes(self):
        store, result = self.run_stage(FakeChat(jitter=True))
        self.assertTrue(result.ok)
        rows = parse_csv(store.files[self.files.remote_final])
        self.assertEqual([r["Name"] for r in rows], ["Jordan", "Riley", "Casey"])
        self.assertEqual(rows[1]["Personalization"], "Great to see your work as Robotics Engineer!")
        self.assertNotIn("Description", rows[0])
        self.assertIs(store.status_of(1), TaskStatus.COMPLETED)

    def test_one_failure_does_not_sink_the_job(self):
        store, result = self.run_stage(FakeChat(fail_on={"Robotics Engineer"}))
        self.assertTrue(result.ok)
        self.assertEqual((result.processed, result.failed), (2, 1))
        rows = parse_csv(store.files[self.files.remote_final])
        self.assertEqual(rows[1]["Personalization"], "")

    def test_all_failures_mark_the_task_error(self):
        store, result = self.run_stage(FakeChat(fail_on={r["Description"][10:] for r in ENRICHED}))
        self.assertFalse(result.ok)
        self.assertIs(store.status_of(1), TaskStatus.ERROR)
        self.assertIn("All 3 generations failed", result.error)

    def test_missing_formatted_file_is_an_error(self):
        store = InMemoryTaskStore()
        result = PersonalizerStage(store, FakeChat(), ExampleBank.from_text("a")).run(self.t)
        self.assertFalse(result.ok)
        self.assertIs(store.status_of(1), TaskStatus.ERROR)

    def test_rows_without_description_are_ignored(self):
        store, result = self.run_stage(FakeChat(), rows=ENRICHED + [{"Name": "X", "LinkedIn": "", "Description": ""}])
        self.assertEqual(result.processed, 3)


if __name__ == "__main__":
    unittest.main()

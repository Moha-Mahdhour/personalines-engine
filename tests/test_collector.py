import tempfile
import unittest
from pathlib import Path

from personalines.enrichment import StaticEnricher
from personalines.jobs import JobFiles, parse_csv
from personalines.pipeline import CollectorStage
from personalines.status import TaskStatus
from personalines.storage import InMemoryTaskStore
from tests.helpers import PROFILES, leads_csv, task


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def stage(self, store, profiles=PROFILES, **kw):
        return CollectorStage(store, StaticEnricher(profiles), self.work, sleep=lambda s: None, **kw)

    def test_happy_path_enriches_and_advances_status(self):
        t = task()
        store = InMemoryTaskStore({JobFiles.for_task(t).remote_input: leads_csv()})
        result = self.stage(store).run(t)
        self.assertTrue(result.ok)
        self.assertEqual((result.processed, result.skipped), (2, 1))
        self.assertEqual([s for s, _ in store.history[1]], [TaskStatus.SEARCHING, TaskStatus.PERSONALIZING])
        rows = parse_csv(store.files[JobFiles.for_task(t).remote_formatted])
        self.assertEqual([r["Name"] for r in rows], ["Jordan", "Riley"])
        self.assertIn("Robotics Engineer", rows[1]["Description"])

    def test_missing_file_fails_after_retries(self):
        store = InMemoryTaskStore()
        result = self.stage(store, download_attempts=2).run(task())
        self.assertFalse(result.ok)
        self.assertIs(store.status_of(1), TaskStatus.ERROR)
        self.assertIn("not found after 2 attempts", store.history[1][-1][1])

    def test_unknown_column_is_reported_clearly(self):
        t = task(field="LinkedIn Profile")
        store = InMemoryTaskStore({JobFiles.for_task(t).remote_input: leads_csv()})
        result = self.stage(store).run(t)
        self.assertFalse(result.ok)
        self.assertIn("'LinkedIn Profile' not found", result.error)

    def test_no_enrichable_leads_is_an_error(self):
        t = task()
        store = InMemoryTaskStore({JobFiles.for_task(t).remote_input: leads_csv()})
        result = self.stage(store, profiles={}).run(t)
        self.assertFalse(result.ok)
        self.assertIs(store.status_of(1), TaskStatus.ERROR)

    def test_unexpected_crash_still_marks_error(self):
        class Boom:
            def enrich(self, urls):
                raise KeyError("sdk exploded")
        t = task()
        store = InMemoryTaskStore({JobFiles.for_task(t).remote_input: leads_csv()})
        result = CollectorStage(store, Boom(), self.work).run(t)
        self.assertFalse(result.ok)
        self.assertIs(store.status_of(1), TaskStatus.ERROR)


if __name__ == "__main__":
    unittest.main()

import threading
import unittest

from personalines.dispatch import Dispatcher
from personalines.status import TaskStatus
from personalines.workers import StageWorker


class Recorder:
    def __init__(self, name):
        self.name, self.tasks = name, []

    def submit(self, task):
        self.tasks.append(task)


def payload(status, task_id=1):
    return {"record": {"id": task_id, "UserID": "u", "FileName": "f.csv", "Status": status, "LinkedinField": "LinkedIn"}}


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.collector, self.personalizer = Recorder("collector"), Recorder("personalizer")
        self.d = Dispatcher({TaskStatus.INIT: self.collector, TaskStatus.PERSONALIZING: self.personalizer})

    def test_routes_by_status(self):
        self.assertEqual(self.d.dispatch(payload("Init")), "collector")
        self.assertEqual(self.d.dispatch(payload("Personalizing")), "personalizer")
        self.assertEqual(len(self.collector.tasks), 1)

    def test_terminal_and_intermediate_updates_are_ignored(self):
        for s in ("Searching", "Completed", "Error"):
            self.assertIsNone(self.d.dispatch(payload(s)))

    def test_duplicate_deliveries_are_dropped(self):
        self.d.dispatch(payload("Init"))
        self.assertIsNone(self.d.dispatch(payload("Init")))
        self.assertEqual(len(self.collector.tasks), 1)

    def test_malformed_payload_is_ignored(self):
        self.assertIsNone(self.d.dispatch({"record": {"id": 1}}))
        self.assertIsNone(self.d.dispatch({"record": "nope"}))

    def test_dedup_memory_is_bounded(self):
        d = Dispatcher({TaskStatus.INIT: self.collector}, memory=2)
        for i in range(5):
            d.dispatch(payload("Init", i))
        self.assertEqual(len(d._seen), 2)


class task_:
    def __init__(self, id):
        self.id = id


class StageWorkerTests(unittest.TestCase):
    def test_objects_without_an_id_do_not_kill_the_thread(self):
        class Stage:
            def run(self, task):
                raise RuntimeError("bug")
        w = StageWorker("test", Stage(), poll_interval=0.01).start()
        w.submit("plain string"); w.submit("another")
        self.assertTrue(w.wait_idle(timeout=5))
        self.assertTrue(w.alive)
        w.stop()

    def test_wait_idle_times_out(self):
        class Slow:
            def run(self, task):
                import time; time.sleep(0.5)
        w = StageWorker("slow", Slow(), poll_interval=0.01).start()
        w.submit(task_(1))
        self.assertFalse(w.wait_idle(timeout=0.05))
        w.wait_idle(timeout=5); w.stop()

    def test_processes_tasks_and_survives_a_crash(self):
        seen, lock = [], threading.Lock()

        class Stage:
            def run(self, task):
                with lock:
                    seen.append(task.id)
                if task.id == "boom":
                    raise RuntimeError("stage bug")

        w = StageWorker("test", Stage(), poll_interval=0.01).start()
        for t in (task_("a"), task_("boom"), task_("b")):
            w.submit(t)
        self.assertTrue(w.wait_idle(timeout=5))
        self.assertEqual(seen, ["a", "boom", "b"])
        self.assertTrue(w.alive)
        w.stop()
        self.assertFalse(w.alive)


if __name__ == "__main__":
    unittest.main()

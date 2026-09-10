import importlib.util
import tempfile
import unittest
from pathlib import Path

from personalines.config import Settings
from personalines.engine import build_engine
from personalines.enrichment import StaticEnricher
from personalines.examples import ExampleBank
from personalines.jobs import JobFiles
from personalines.status import TaskStatus
from personalines.storage import InMemoryTaskStore
from tests.helpers import PROFILES, EchoChat, leads_csv, record, task

HAVE_WEB = all(importlib.util.find_spec(m) for m in ("fastapi", "httpx"))


@unittest.skipUnless(HAVE_WEB, "needs the 'webhook' extra and httpx (installed in CI)")
class WebhookTests(unittest.TestCase):
    def test_health_and_task_routing(self):
        from fastapi.testclient import TestClient
        from personalines.entrypoints.webhook import create_app

        with tempfile.TemporaryDirectory() as d:
            store = InMemoryTaskStore({JobFiles.for_task(task()).remote_input: leads_csv()})
            engine = build_engine(Settings(work_dir=Path(d)), store=store, enricher=StaticEnricher(PROFILES),
                                  chat=EchoChat(), examples=ExampleBank.from_text("a"))
            with TestClient(create_app(engine)) as client:
                health = client.get("/healthz").json()
                self.assertEqual(health, {"ok": True, "workers": {"collector": True, "personalizer": True}})
                self.assertEqual(client.post("/api", json=record("Init")).json(), {"routed_to": "collector"})
                self.assertTrue(engine.workers[0].wait_idle(timeout=10))
                self.assertEqual(client.post("/api", json={"record": {"id": 1}}).json(), {"routed_to": None})
            self.assertIs(store.status_of(1), TaskStatus.PERSONALIZING)


if __name__ == "__main__":
    unittest.main()

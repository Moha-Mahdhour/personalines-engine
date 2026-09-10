import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from personalines.config import Settings
from personalines.engine import build_engine
from personalines.enrichment import StaticEnricher
from personalines.examples import ExampleBank
from personalines.jobs import JobFiles, parse_csv
from personalines.status import TaskStatus
from personalines.storage import InMemoryTaskStore
from tests.helpers import PROFILES, EchoChat, leads_csv, record, task

ROOT = Path(__file__).resolve().parent.parent


class EndToEndTests(unittest.TestCase):
    def test_full_job_runs_from_init_to_completed_in_memory(self):
        with tempfile.TemporaryDirectory() as d:
            settings = Settings(work_dir=Path(d), max_concurrency=2)
            files = JobFiles.for_task(task())
            store = InMemoryTaskStore({files.remote_input: leads_csv()})
            engine = build_engine(settings, store=store, enricher=StaticEnricher(PROFILES), chat=EchoChat(),
                                  examples=ExampleBank.from_text("a\nb"), rng=random.Random(0)).start()
            try:
                self.assertEqual(engine.dispatcher.dispatch(record("Init")), "collector")
                self.assertTrue(engine.workers[0].wait_idle(timeout=10))
                # In production the collector's status update fires the next webhook.
                self.assertEqual(engine.dispatcher.dispatch(record("Personalizing")), "personalizer")
                self.assertTrue(engine.workers[1].wait_idle(timeout=10))
            finally:
                engine.stop()
            self.assertEqual([s for s, _ in store.history[1]],
                             [TaskStatus.SEARCHING, TaskStatus.PERSONALIZING, TaskStatus.COMPLETED])
            final = parse_csv(store.files[files.remote_final])
            self.assertEqual([r["Personalization"] for r in final],
                             ["Line for Head of Operations", "Line for Robotics Engineer"])

    def test_missing_credentials_fail_fast_when_building_real_adapters(self):
        from personalines.config import ConfigError
        with self.assertRaises(ConfigError):
            build_engine(Settings())


class CliTests(unittest.TestCase):
    def run_cli(self, *args, env=None):
        base = {k: v for k, v in os.environ.items() if not k.startswith(("SUPABASE", "OPENAI", "PROXYCURL"))}
        return subprocess.run([sys.executable, "-m", "personalines", *args], cwd=ROOT, env={**base, **(env or {})},
                              capture_output=True, text=True, timeout=30)

    def test_help_works_without_optional_dependencies(self):
        r = self.run_cli("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("webhook", r.stdout)

    def test_check_reports_missing_config_with_exit_code_2(self):
        r = self.run_cli("check")
        self.assertEqual(r.returncode, 2)
        self.assertIn("OPENAI_API_KEY", r.stderr)

    def test_check_passes_with_full_config(self):
        secrets = {"SUPABASE_SECRET": "sekret-supa", "PROXYCURL_SECRET": "sekret-proxy", "OPENAI_API_KEY": "sekret-openai"}
        r = self.run_cli("check", env={"SUPABASE_URL": "https://abc.supabase.co", **secrets})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("config ok", r.stdout)
        for value in secrets.values():
            self.assertNotIn(value, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()

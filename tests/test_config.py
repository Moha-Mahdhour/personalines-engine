import unittest
from pathlib import Path

from personalines.config import ConfigError, Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_when_env_empty(self):
        s = Settings.from_env({})
        self.assertEqual(s.openai_model, "gpt-3.5-turbo")
        self.assertEqual(s.storage_bucket, "Users")
        self.assertEqual(s.max_concurrency, 8)
        self.assertEqual(s.work_dir, Path("Filing"))

    def test_reads_values_and_types(self):
        s = Settings.from_env({
            "SUPABASE_URL": "https://abcdefghijklmnop.supabase.co",
            "SUPABASE_SECRET": "k", "OPENAI_API_KEY": "o", "PROXYCURL_SECRET": "p",
            "MAX_CONCURRENCY": "3", "REQUEST_TIMEOUT": "7.5", "PORT": "8080",
        })
        self.assertEqual(s.max_concurrency, 3)
        self.assertEqual(s.request_timeout, 7.5)
        self.assertEqual(s.webhook_port, 8080)
        self.assertEqual(s.supabase_project_id, "abcdefghijklmnop")

    def test_invalid_integer_is_a_config_error(self):
        with self.assertRaisesRegex(ConfigError, "MAX_CONCURRENCY"):
            Settings.from_env({"MAX_CONCURRENCY": "lots"})

    def test_below_minimum_is_rejected(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"MAX_CONCURRENCY": "0"})

    def test_require_lists_every_missing_variable(self):
        s = Settings.from_env({"SUPABASE_URL": "https://x.supabase.co"})
        with self.assertRaises(ConfigError) as ctx:
            s.require("supabase_url", "supabase_key", "openai_api_key")
        msg = str(ctx.exception)
        self.assertIn("SUPABASE_SECRET", msg)
        self.assertIn("OPENAI_API_KEY", msg)
        self.assertNotIn("SUPABASE_URL", msg)

    def test_project_id_empty_for_non_supabase_host(self):
        self.assertEqual(Settings.from_env({"SUPABASE_URL": "http://localhost:54321"}).supabase_project_id, "")


if __name__ == "__main__":
    unittest.main()

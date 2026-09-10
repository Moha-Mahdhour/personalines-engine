import tempfile
import unittest
from pathlib import Path

from personalines.jobs import JobFiles, parse_csv, render_csv, write_local


class JobFilesTests(unittest.TestCase):
    def test_remote_keys_match_web_app_convention(self):
        j = JobFiles("u-1", 42, "leads.csv")
        self.assertEqual(j.remote_input, "u-1/42/leads.csv")
        self.assertEqual(j.remote_formatted, "u-1/42/leads-formatted.csv")
        self.assertEqual(j.remote_final, "u-1/42/leads-formatted-Final.csv")

    def test_dotted_names_keep_legacy_remote_keys(self):
        j = JobFiles("u", 1, "leads.v2.csv")
        self.assertEqual(j.remote_formatted, "u/1/leads.v2-formatted.csv")
        self.assertEqual(j.remote_final, "u/1/leads-formatted-Final.csv")

    def test_local_paths_share_one_stem(self):
        j = JobFiles("u", 1, "leads.v2.csv", Path("/tmp/work"))
        self.assertEqual(j.local_input, Path("/tmp/work/u/1/leads.v2.csv"))
        self.assertEqual(j.local_formatted.name, "leads.v2-formatted.csv")
        self.assertEqual(j.local_final.name, "leads.v2-final.csv")


class CsvTests(unittest.TestCase):
    def test_round_trip(self):
        rows = [{"Name": "A", "LinkedIn": "https://x/a"}, {"Name": "B", "LinkedIn": "https://x/b"}]
        self.assertEqual(parse_csv(render_csv(rows)), rows)

    def test_excel_bom_is_ignored(self):
        self.assertEqual(parse_csv("﻿Name\nA\n".encode("utf-8"))[0], {"Name": "A"})

    def test_columns_cover_every_row(self):
        out = parse_csv(render_csv([{"a": "1"}, {"a": "2", "b": "3"}]))
        self.assertEqual(out[0], {"a": "1", "b": ""})

    def test_write_local_creates_parents(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_local(Path(d, "x", "y", "f.csv"), b"a\n1\n")
            self.assertEqual(p.read_bytes(), b"a\n1\n")


if __name__ == "__main__":
    unittest.main()

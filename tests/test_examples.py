import random
import tempfile
import unittest
from pathlib import Path

from personalines.examples import ExampleBank


class ExampleBankTests(unittest.TestCase):
    def test_bundled_examples_load(self):
        bank = ExampleBank.default()
        self.assertGreaterEqual(len(bank.lines), 7)

    def test_blank_comment_and_duplicate_lines_are_dropped(self):
        bank = ExampleBank.from_text("a\n\n# note\nb\na\n  c  \n")
        self.assertEqual(bank.lines, ("a", "b", "c"))

    def test_sample_never_exceeds_available_lines(self):
        bank = ExampleBank.from_text("a\nb\nc")
        self.assertEqual(len(bank.sample(7)), 3)

    def test_sampling_is_reproducible_with_a_seed(self):
        bank = ExampleBank.default()
        self.assertEqual(bank.sample(5, random.Random(1)), bank.sample(5, random.Random(1)))

    def test_block_format(self):
        bank = ExampleBank.from_text("one")
        self.assertEqual(bank.block(3), "Example: one")

    def test_from_file_and_empty_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "ex.txt"); p.write_text("x\ny\n")
            self.assertEqual(ExampleBank.from_file(p).lines, ("x", "y"))
        with self.assertRaises(ValueError):
            ExampleBank.from_text("\n\n")


if __name__ == "__main__":
    unittest.main()

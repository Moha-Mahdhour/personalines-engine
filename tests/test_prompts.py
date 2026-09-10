import unittest

from personalines.prompts import SYSTEM_PROMPT, build_messages, clean_completion


class PromptTests(unittest.TestCase):
    def test_messages_have_system_then_user(self):
        msgs = build_messages("Headline: Engineer", "Example: Nice work!")
        self.assertEqual([m["role"] for m in msgs], ["system", "user"])
        self.assertEqual(msgs[0]["content"], SYSTEM_PROMPT)
        self.assertIn("Headline: Engineer", msgs[1]["content"])
        self.assertIn("Example: Nice work!", msgs[1]["content"])

    def test_braces_in_profile_do_not_break_rendering(self):
        msgs = build_messages('Summary: {"likes": "robots"} and ${weird}', "Example: x")
        self.assertIn('{"likes": "robots"}', msgs[1]["content"])

    def test_long_profiles_are_truncated(self):
        msgs = build_messages("x" * 50_000, "Example: y", max_profile_chars=100)
        self.assertLess(len(msgs[1]["content"]), 2_000)
        self.assertTrue(msgs[1]["content"].endswith("..."))

    def test_word_limit_is_injected(self):
        self.assertIn("under 12 words", build_messages("p", "e", max_words=12)[1]["content"])

    def test_clean_completion_strips_quotes_and_space(self):
        self.assertEqual(clean_completion('  "Great to see your work on robotics!"  '), "Great to see your work on robotics!")
        self.assertEqual(clean_completion("“Smart quotes too.”"), "Smart quotes too.")
        self.assertEqual(clean_completion('Keep "inner" quotes'), 'Keep "inner" quotes')
        self.assertEqual(clean_completion(None), "")


if __name__ == "__main__":
    unittest.main()

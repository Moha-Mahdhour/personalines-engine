import unittest

from personalines.enrichment import ProxycurlEnricher, StaticEnricher, normalize_linkedin_url


class NormalizeTests(unittest.TestCase):
    def test_accepts_common_forms(self):
        for raw in ["https://www.linkedin.com/in/jordan-lee/", "linkedin.com/in/jordan-lee",
                    "http://uk.linkedin.com/in/jordan-lee?trk=abc", "  https://linkedin.com/in/jordan-lee  "]:
            url = normalize_linkedin_url(raw)
            self.assertIsNotNone(url, raw)
            self.assertTrue(url.startswith("http"))
            self.assertTrue(url.endswith("/in/jordan-lee"), url)

    def test_rejects_non_profiles(self):
        for raw in [None, "", "Not Found", "https://www.linkedin.com/company/acme", "https://example.com/in/x"]:
            self.assertIsNone(normalize_linkedin_url(raw), raw)


class StaticEnricherTests(unittest.TestCase):
    def test_results_align_with_input_and_skip_invalid(self):
        e = StaticEnricher({"https://linkedin.com/in/a": {"headline": "A"}})
        out = e.enrich(["linkedin.com/in/a/", "", "https://linkedin.com/in/unknown"])
        self.assertEqual(out, [{"headline": "A"}, None, None])
        self.assertEqual(len(e.requested), 2)   # the blank cell never reached the "API"


class ProxycurlEnricherTests(unittest.TestCase):
    def test_requires_key(self):
        with self.assertRaises(ValueError):
            ProxycurlEnricher("")

    def test_all_invalid_urls_return_without_touching_the_sdk(self):
        # Returns before importing the SDK, so this passes without it installed.
        self.assertEqual(ProxycurlEnricher("k").enrich(["", None, "Not Found"]), [None, None, None])


if __name__ == "__main__":
    unittest.main()

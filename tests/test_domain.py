import unittest

from personalines.domain import Date, Profile, Task
from personalines.status import TaskStatus

RECORD = {"id": 1077, "UserID": "u-1", "FileName": "leads.csv", "Status": "Init", "LinkedinField": "LinkedIn URL"}


class TaskTests(unittest.TestCase):
    def test_from_webhook_payload(self):
        t = Task.from_payload({"type": "INSERT", "record": RECORD})
        self.assertEqual((t.id, t.user_id, t.file_name), (1077, "u-1", "leads.csv"))
        self.assertIs(t.status, TaskStatus.INIT)
        self.assertEqual(t.linkedin_field, "LinkedIn URL")

    def test_bare_record_is_accepted(self):
        self.assertEqual(Task.from_payload(RECORD).id, 1077)

    def test_missing_field_names_the_field(self):
        bad = {k: v for k, v in RECORD.items() if k != "FileName"}
        with self.assertRaisesRegex(ValueError, "FileName"):
            Task.from_record(bad)

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(ValueError):
            Task.from_record({**RECORD, "Status": "Queued"})


PROXYCURL = {
    "full_name": "Jordan Lee", "headline": "Head of Operations", "occupation": "Operations at Acme",
    "summary": "  Scaling support teams.  ", "city": "Austin", "state": "Texas", "country_full_name": "United States",
    "experiences": [
        {"title": "Head of Operations", "company": "Acme", "starts_at": {"day": 1, "month": 3, "year": 2021}, "ends_at": None,
         "location": "Austin", "description": None},
        {"title": "Analyst", "company": "Beta", "starts_at": None, "ends_at": None},
    ],
    "education": [{"school": "State University", "degree_name": "BS", "field_of_study": "Economics",
                   "starts_at": {"year": 2012}, "ends_at": {"year": 2016}}],
    "certifications": [{"name": "Six Sigma Green Belt", "starts_at": None}, {"name": None}],
}


class ProfileTests(unittest.TestCase):
    def test_parses_partial_profile(self):
        p = Profile.from_proxycurl(PROXYCURL)
        self.assertEqual(p.summary, "Scaling support teams.")
        self.assertEqual(len(p.experiences), 2)
        self.assertIsNone(p.experiences[0].end)
        self.assertEqual(p.education[0].degree, "BS")
        self.assertEqual([c.name for c in p.certifications], ["Six Sigma Green Belt"])

    def test_prompt_text_contains_the_useful_facts(self):
        text = Profile.from_proxycurl(PROXYCURL).to_prompt_text()
        self.assertIn("Head of Operations at Acme (2021-03 to present; Austin)", text)
        self.assertIn("State University: BS, Economics (2012 to 2016)", text)
        self.assertIn("Certifications: Six Sigma Green Belt", text)
        self.assertIn("Location: Austin, Texas, United States", text)

    def test_prompt_text_omits_names_and_empty_fields(self):
        text = Profile.from_proxycurl({"headline": "Engineer"}).to_prompt_text()
        self.assertEqual(text, "Headline: Engineer")
        self.assertNotIn("Jordan", Profile.from_proxycurl(PROXYCURL).to_prompt_text())

    def test_date_formatting(self):
        self.assertEqual(str(Date(2020, 7)), "2020-07")
        self.assertEqual(str(Date(2020)), "2020")
        self.assertIsNone(Date.parse(None))
        self.assertIsNone(Date.parse({"day": 1}))


if __name__ == "__main__":
    unittest.main()

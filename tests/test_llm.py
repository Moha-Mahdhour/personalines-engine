import json
import unittest

from personalines.llm import LLMError, OpenAIChatClient

OK = json.dumps({"choices": [{"message": {"content": "Nice work on the robot!"}}]}).encode()


class FakeTransport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def __call__(self, url, headers, body, timeout):
        self.calls.append(json.loads(body))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def client(transport, **kw):
    sleeps = []
    c = OpenAIChatClient("sk-test", "test-model", transport=transport, sleep=sleeps.append, rng=lambda: 0.0, **kw)
    return c, sleeps


class OpenAIClientTests(unittest.TestCase):
    def test_success_returns_content_and_sends_model(self):
        t = FakeTransport((200, OK))
        c, sleeps = client(t)
        self.assertEqual(c.complete([{"role": "user", "content": "hi"}]), "Nice work on the robot!")
        self.assertEqual(t.calls[0]["model"], "test-model")
        self.assertEqual(sleeps, [])

    def test_retries_rate_limits_with_exponential_backoff(self):
        t = FakeTransport((429, b"slow down"), (503, b"busy"), (200, OK))
        c, sleeps = client(t, base_delay=1.0)
        self.assertEqual(c.complete([]), "Nice work on the robot!")
        self.assertEqual(sleeps, [1.0, 2.0])

    def test_network_errors_are_retried(self):
        c, _ = client(FakeTransport(TimeoutError("t"), ConnectionError("c"), (200, OK)))
        self.assertEqual(c.complete([]), "Nice work on the robot!")

    def test_auth_errors_fail_immediately(self):
        t = FakeTransport((401, b"bad key"), (200, OK))
        c, sleeps = client(t)
        with self.assertRaisesRegex(LLMError, "401"):
            c.complete([])
        self.assertEqual(len(t.calls), 1)
        self.assertEqual(sleeps, [])

    def test_gives_up_after_max_retries(self):
        c, sleeps = client(FakeTransport(*[(500, b"x")] * 4), max_retries=3)
        with self.assertRaisesRegex(LLMError, "4 attempts"):
            c.complete([])
        self.assertEqual(len(sleeps), 3)

    def test_backoff_is_capped(self):
        c, _ = client(FakeTransport(), base_delay=1.0, max_delay=5.0)
        self.assertEqual(c._backoff(10), 5.0)

    def test_malformed_body_is_retried_then_reported(self):
        c, _ = client(FakeTransport((200, b"{}"), (200, b"not json")), max_retries=1)
        with self.assertRaisesRegex(LLMError, "malformed"):
            c.complete([])

    def test_missing_key_rejected_at_construction(self):
        with self.assertRaises(LLMError):
            OpenAIChatClient("")


if __name__ == "__main__":
    unittest.main()

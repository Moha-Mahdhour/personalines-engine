import unittest

from personalines.status import TaskStatus
from personalines.storage import InMemoryTaskStore, StorageError, SupabaseTaskStore


class InMemoryStoreTests(unittest.TestCase):
    def test_upload_then_download(self):
        s = InMemoryTaskStore()
        s.upload("u/1/f.csv", b"a\n")
        self.assertEqual(s.download("u/1/f.csv"), b"a\n")

    def test_missing_file_raises_storage_error(self):
        with self.assertRaises(StorageError):
            InMemoryTaskStore().download("nope")

    def test_status_history_is_recorded_in_order(self):
        s = InMemoryTaskStore()
        s.set_status(7, TaskStatus.SEARCHING)
        s.set_status(7, TaskStatus.ERROR, "boom")
        self.assertEqual(s.history[7], [(TaskStatus.SEARCHING, None), (TaskStatus.ERROR, "boom")])
        self.assertIs(s.status_of(7), TaskStatus.ERROR)
        self.assertIsNone(s.status_of(8))


class SupabaseStoreTests(unittest.TestCase):
    def test_construction_does_not_touch_the_network_or_sdk(self):
        store = SupabaseTaskStore("https://x.supabase.co", "key")
        self.assertIsNone(store._client)


if __name__ == "__main__":
    unittest.main()

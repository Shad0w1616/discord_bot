import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import sys

sys.modules.setdefault("dotenv", SimpleNamespace(load_dotenv=lambda: None))

from music.models import Track
from music.queue import MusicQueue
from music.storage import QueueStorage


def track(title: str) -> Track:
    return Track(title=title, url=f"https://example.com/{title}", guild_id=1)


class MusicQueueTests(unittest.TestCase):
    def test_remove_uses_visible_one_based_position(self) -> None:
        queue = MusicQueue()
        queue.add_many([track("one"), track("two"), track("three")])

        removed = queue.remove(2)

        self.assertEqual(removed.title, "two")
        self.assertEqual([item.title for item in queue.all()], ["one", "three"])

    def test_pages_do_not_modify_queue(self) -> None:
        queue = MusicQueue()
        queue.add_many([track(str(index)) for index in range(15)])

        self.assertEqual([item.title for item in queue.page(2, 10)], [str(i) for i in range(10, 15)])
        self.assertEqual(queue.size(), 15)


class QueueStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_round_trip_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = QueueStorage(Path(directory) / "queues.json")
            original = [track("one"), track("two")]

            await storage.save(1, original)
            restored = await storage.load(1)

            self.assertEqual([item.title for item in restored], ["one", "two"])
            await storage.save(1, [])
            self.assertEqual(await storage.load(1), [])


if __name__ == "__main__":
    unittest.main()

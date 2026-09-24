import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cogs.daily_victims import (
    CATEGORIES,
    DailyVictimsStorage,
    build_message,
    choose_members,
)


class DailyVictimsMessageTests(unittest.TestCase):
    def test_uses_unique_members_when_possible(self) -> None:
        members = [SimpleNamespace(mention=f"<@{index}>") for index in range(10)]

        selected = choose_members(members)

        self.assertEqual(len(selected), len(CATEGORIES))
        self.assertEqual(
            len({member.mention for member in selected}),
            len(CATEGORIES),
        )

    def test_message_contains_all_categories_and_mentions(self) -> None:
        members = [
            SimpleNamespace(mention=f"<@{index}>")
            for index in range(len(CATEGORIES))
        ]

        message = build_message(members)

        self.assertIn("Жертвы движухи", message)
        for category, member in zip(CATEGORIES, members):
            self.assertIn(f"**{category}** — {member.mention}", message)


class DailyVictimsStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_configuration_and_sent_date_survive_reload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.json"
            storage = DailyVictimsStorage(path)
            await storage.configure(10, 20)
            await storage.mark_sent(10, "2026-09-24")

            restored = DailyVictimsStorage(path)
            data = await restored.all()

            self.assertEqual(data["10"]["channel_id"], 20)
            self.assertTrue(await restored.is_sent(10, "2026-09-24"))


if __name__ == "__main__":
    unittest.main()

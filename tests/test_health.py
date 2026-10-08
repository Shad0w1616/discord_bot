import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app
from cogs.playlists import PlaylistCommands


class HealthTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_requires_live_discord_connection(self):
        for ready, closed, status in [(False, False, 503), (True, False, 200), (True, True, 503)]:
            with patch.object(app, 'bot', SimpleNamespace(is_ready=Mock(return_value=ready), is_closed=Mock(return_value=closed))):
                self.assertEqual((await app.health(None)).status, status)

    async def test_playlist_group_registers_all_commands(self):
        bot = app.NotoriousBot()
        try:
            await bot.add_cog(PlaylistCommands(bot))
            group = bot.tree.get_command('playlist')
            self.assertEqual({c.name for c in group.commands}, {'create', 'list', 'show', 'play', 'remove', 'delete'})
        finally:
            await bot.close()

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from music.models import Track
from music.playlists import PlaylistStore
from tests import test_player_controls


class PlaylistTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'playlists.sqlite3'
        self.store = PlaylistStore(self.path)

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_persistence_names_and_scope(self):
        track = Track('One', 'https://youtube.com/watch?v=one', 1)
        await self.store.execute('add', 1, 2, '  My   songs ', track=track)
        reopened = PlaylistStore(self.path)
        self.assertEqual(await reopened.execute('get', 1, 2, 'my SONGS'), [track])
        self.assertEqual(await reopened.execute('list', 2, 2), [])
        self.assertEqual(await reopened.execute('list', 1, 3), [])
        with self.assertRaises(ValueError):
            await reopened.execute('delete', 1, 3, 'My songs')
        with self.assertRaises(ValueError):
            await reopened.execute('create', 1, 2, 'my songs')

    async def test_concurrent_adds_and_duplicates(self):
        tracks = [Track(str(i), f'https://youtube.com/watch?v={i}', 1) for i in range(12)]
        await asyncio.gather(*(self.store.execute('add', 1, 2, 'Mix', track=t) for t in tracks))
        self.assertEqual(len(await self.store.execute('get', 1, 2, 'Mix')), 12)
        with self.assertRaises(ValueError):
            await self.store.execute('add', 1, 2, 'Mix', track=tracks[0])
        self.assertEqual(await self.store.execute('list', 1, 2), [('Mix', 12)])

    async def test_create_remove_delete_and_validation(self):
        for name in ['', '   ', 'a' * 51]:
            with self.assertRaises(ValueError):
                await self.store.execute('create', 1, 2, name)
        await self.store.execute('create', 1, 2, 'Mix')
        self.assertEqual(await self.store.execute('get', 1, 2, 'Mix'), [])
        await self.store.execute('add', 1, 2, 'Mix', track=Track('One', 'url', 1))
        with self.assertRaises(ValueError):
            await self.store.execute('remove', 1, 2, 'Mix', position=2)
        await self.store.execute('remove', 1, 2, 'Mix', position=1)
        self.assertEqual(await self.store.execute('get', 1, 2, 'Mix'), [])
        await self.store.execute('delete', 1, 2, 'Mix')
        self.assertEqual(await self.store.execute('list', 1, 2), [])


class SaveButtonTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_player_controls.ControlsTests.asyncSetUp
    asyncTearDown = test_player_controls.ControlsTests.asyncTearDown

    async def test_button_captures_track_and_modal_checks_owner(self):
        store = SimpleNamespace(execute=AsyncMock())
        self.interaction.client = SimpleNamespace(playlists=store)
        self.interaction.user.id = 42
        self.interaction.response.send_modal = AsyncMock()
        await self.panel.save_playlist.callback(self.interaction)
        modal = self.interaction.response.send_modal.call_args.args[0]
        self.player.current = Track('Next', 'next-url', 1)
        modal.name._value = 'Mix'
        self.interaction.user.id = 43
        await modal.on_submit(self.interaction)
        store.execute.assert_not_awaited()
        self.interaction.user.id = 42
        await modal.on_submit(self.interaction)
        self.assertEqual(store.execute.call_args.kwargs['track'].title, 'One')
        modal.stop()

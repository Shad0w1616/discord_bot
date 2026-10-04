import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from music.controls import PlayerControls, RemoveTrackModal
from music.models import Track
from music.queue import MusicQueue


class ControlsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.player = SimpleNamespace(
            history=[], current=Track("One", "url", 1), guild_id=1,
            queue=MusicQueue(), wave_active=False, _shutting_down=False,
            repeat_enabled=False, voice_client=Mock(channel=SimpleNamespace(id=2)),
            shutdown=AsyncMock(), remove=AsyncMock(),
        )
        self.player.voice_client.is_paused.return_value = False
        self.player.voice_client.is_connected.return_value = True
        self.panel = PlayerControls(self.player)
        self.player.panel_view = self.panel
        self.interaction = SimpleNamespace(
            guild_id=1, user=SimpleNamespace(
                voice=SimpleNamespace(channel=SimpleNamespace(id=2)),
                guild_permissions=SimpleNamespace(administrator=False),
            ),
            response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    async def asyncTearDown(self):
        self.panel.stop()

    async def test_other_channel_and_stale_panels_are_rejected(self):
        self.interaction.user.voice.channel.id = 3
        self.assertFalse(await self.panel.interaction_check(self.interaction))
        self.interaction.user.voice.channel.id = 2
        self.assertTrue(await self.panel.interaction_check(self.interaction))
        self.player.panel_view = None
        self.assertFalse(await self.panel.interaction_check(self.interaction))

    async def test_stop_preserves_admin_permissions(self):
        await self.panel.run_action(self.interaction, "stop")
        self.player.shutdown.assert_not_awaited()
        self.interaction.user.guild_permissions.administrator = True
        await self.panel.run_action(self.interaction, "stop")
        self.player.shutdown.assert_awaited_once()

    async def test_wave_stop_is_available_to_same_channel_listener(self):
        self.player.wave_active = True
        self.player.stop_wave = AsyncMock()
        await self.panel.run_action(self.interaction, "stop")
        self.player.stop_wave.assert_awaited_once()
        self.player.shutdown.assert_not_awaited()

    async def test_removal_modal_rechecks_channel_and_queue_snapshot(self):
        track = self.player.current
        self.player.queue.add(track)
        modal = RemoveTrackModal(self.panel)
        modal.position._value = "1"
        self.player.queue.clear()
        self.player.queue.add(Track("Two", "another", 1))
        await modal.on_submit(self.interaction)
        self.player.remove.assert_not_awaited()
        self.player.queue.clear()
        self.player.queue.add(track)
        self.interaction.user.voice.channel.id = 3
        await modal.on_submit(self.interaction)
        self.player.remove.assert_not_awaited()
        modal.stop()

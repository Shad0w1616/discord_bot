import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
from discord.ext import commands

from cogs.daily_victims import DailyVictims
from music.controls import PlayerControls, SaveTrackModal
from music.models import Track
from music.player import MusicPlayer
from services.channel_policy import (
    ChannelCommandTree, MUSIC_COMMANDS, TARGET_GUILD_ID,
    MUSIC_CHANNEL_ID, VICTIMS_CHANNEL_ID, check_channel, routed_channel,
)


class ChannelPolicyTests(unittest.IsolatedAsyncioTestCase):
    def interaction(self, command="play", channel=VICTIMS_CHANNEL_ID, guild=TARGET_GUILD_ID):
        return SimpleNamespace(
            guild_id=guild, channel_id=channel, data={"name": command},
            response=SimpleNamespace(is_done=Mock(return_value=False), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    async def test_music_rejected_outside_fm_with_private_link(self):
        for name in MUSIC_COMMANDS:
            interaction = self.interaction(name)
            self.assertFalse(await ChannelCommandTree.interaction_check(None, interaction))
            args = interaction.response.send_message.call_args
            self.assertTrue(args.kwargs["ephemeral"])
            self.assertIn(f"<#{MUSIC_CHANNEL_ID}>", args.args[0])
        self.assertTrue(await check_channel(self.interaction(channel=MUSIC_CHANNEL_ID)))
        self.assertFalse(await check_channel(self.interaction(channel=123)))  # Includes threads.

    async def test_other_guilds_and_unrelated_commands_unchanged(self):
        for name in [*MUSIC_COMMANDS, "victims", "victims_setup", "victims_disable"]:
            interaction = self.interaction(name, guild=123)
            self.assertTrue(await ChannelCommandTree.interaction_check(None, interaction))
            interaction.response.send_message.assert_not_awaited()
        self.assertTrue(await ChannelCommandTree.interaction_check(None, self.interaction("help")))

    async def test_victims_commands_only_in_general(self):
        for name in ["victims", "victims_setup", "victims_disable"]:
            self.assertTrue(await ChannelCommandTree.interaction_check(None, self.interaction(name)))
            wrong = self.interaction(name, channel=MUSIC_CHANNEL_ID)
            self.assertFalse(await ChannelCommandTree.interaction_check(None, wrong))
            self.assertIn(f"<#{VICTIMS_CHANNEL_ID}>", wrong.response.send_message.call_args.args[0])

    async def test_player_messages_override_old_channel_and_survive_rename(self):
        fm = SimpleNamespace(id=MUSIC_CHANNEL_ID, name="renamed", send=AsyncMock())
        guild = SimpleNamespace(id=TARGET_GUILD_ID, name="renamed guild", get_channel=Mock(return_value=fm))
        player = object.__new__(MusicPlayer)
        player.voice_client = SimpleNamespace(guild=guild)
        old = SimpleNamespace(send=AsyncMock())
        player.text_channel = old
        await player._notify("Next track")
        fm.send.assert_awaited_once_with("Next track")
        old.send.assert_not_awaited()
        guild.get_channel.return_value = None
        with self.assertRaises(RuntimeError):
            routed_channel(guild, old)
        guild.id = 123
        self.assertIs(player.text_channel, old)

    async def test_rubric_redirects_even_with_stale_schedule_channel(self):
        general = SimpleNamespace(send=AsyncMock())
        old = SimpleNamespace(send=AsyncMock())
        guild = SimpleNamespace(id=TARGET_GUILD_ID, get_channel=Mock(return_value=general))
        cog = object.__new__(DailyVictims)
        cog._eligible_members = AsyncMock(return_value=[SimpleNamespace(mention="<@1>")])
        await cog._send_rubric(guild, old)
        general.send.assert_awaited_once()
        old.send.assert_not_awaited()
        guild.get_channel.assert_called_once_with(VICTIMS_CHANNEL_ID)

    async def test_old_panel_and_save_form_cannot_bypass_channel_check(self):
        wrong = self.interaction()
        self.assertFalse(await PlayerControls.interaction_check(None, wrong))
        store = SimpleNamespace(execute=AsyncMock())
        modal = SaveTrackModal(store, TARGET_GUILD_ID, 1, Track("Song", "url", TARGET_GUILD_ID))
        try:
            await modal.on_submit(wrong)
            store.execute.assert_not_awaited()
        finally:
            modal.stop()

    async def test_all_registered_music_commands_are_covered(self):
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.none(), tree_cls=ChannelCommandTree)
        try:
            for extension in ["cogs.music", "cogs.admin", "cogs.playlists"]:
                await bot.load_extension(extension)
            self.assertEqual({c.name for c in bot.tree.get_commands()}, MUSIC_COMMANDS)
        finally:
            await bot.close()

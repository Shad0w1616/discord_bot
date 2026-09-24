from __future__ import annotations

import asyncio

import discord

from music.player import MusicPlayer
from music.storage import QueueStorage
from settings import settings
from utils.logger import logger


class VoiceManager:
    """Управляет одним голосовым плеером на Discord-сервер."""

    def __init__(self, bot) -> None:
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}
        self.storage = QueueStorage(settings.QUEUE_STATE_PATH)

    async def connect(
        self,
        member: discord.Member,
        text_channel: discord.TextChannel,
    ) -> MusicPlayer:
        if not member.voice or not member.voice.channel:
            raise RuntimeError("Сначала зайдите в голосовой канал.")

        guild_id = member.guild.id
        voice_channel = member.voice.channel
        existing = self.players.get(guild_id)
        if existing and existing.voice_client.is_connected():
            if existing.voice_client.channel.id != voice_channel.id:
                raise RuntimeError("Бот уже играет в другом голосовом канале.")
            existing.text_channel = text_channel
            return existing
        if existing:
            self.players.pop(guild_id, None)

        try:
            voice_client = await voice_channel.connect(
                timeout=70.0,
                reconnect=True,
                self_deaf=True,
                self_mute=False,
            )
        except asyncio.TimeoutError as error:
            raise RuntimeError(
                "Discord не ответил вовремя. Проверьте права Connect и Speak."
            ) from error
        except discord.ClientException as error:
            raise RuntimeError(f"Ошибка подключения: {error}") from error

        player = MusicPlayer(
            voice_client,
            text_channel,
            self.bot.loop,
            self.storage,
        )
        self.players[guild_id] = player
        restored = await player.restore()
        if restored:
            logger.info("Восстановлено треков guild=%s: %s", guild_id, restored)
            asyncio.create_task(player.play_next())
        logger.info("Voice connected: %s", voice_channel.name)
        return player

    def get_player(self, guild_id: int) -> MusicPlayer | None:
        return self.players.get(guild_id)

    async def disconnect(self, guild_id: int) -> None:
        player = self.players.get(guild_id)
        if not player:
            return
        try:
            await player.shutdown()
        except Exception:
            logger.exception("Ошибка shutdown player")
        finally:
            self.players.pop(guild_id, None)

    async def shutdown(self) -> None:
        guilds = list(self.players)
        for guild_id in guilds:
            player = self.players[guild_id]
            try:
                await player.shutdown(preserve_queue=True)
            except Exception:
                logger.exception("Ошибка сохранения player guild=%s", guild_id)
            finally:
                self.players.pop(guild_id, None)

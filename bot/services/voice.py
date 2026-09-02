from __future__ import annotations

import asyncio
from typing import Dict

import discord

from music.player import MusicPlayer

from utils.logger import logger


class VoiceManager:
    """
    Управление Discord voice-подключениями.

    Один guild_id -> один MusicPlayer.
    """

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        self.players: Dict[
            int,
            MusicPlayer
        ] = {}

    async def connect(
        self,
        member: discord.Member,
        text_channel: discord.TextChannel
    ) -> MusicPlayer:
        """
        Подключает бота к голосовому каналу пользователя
        и возвращает активный MusicPlayer.
        """

        if not member.voice or not member.voice.channel:

            raise RuntimeError(
                "Пользователь не находится в голосовом канале."
            )

        guild_id = member.guild.id
        voice_channel = member.voice.channel

        existing = self.players.get(
            guild_id
        )

        if existing:

            if existing.voice_client.is_connected():

                if (
                    existing.voice_client.channel.id
                    !=
                    voice_channel.id
                ):

                    await existing.voice_client.move_to(
                        voice_channel
                    )

                existing.text_channel = text_channel

                return existing

            else:

                self.players.pop(
                    guild_id,
                    None
                )

        try:

            voice_client = await voice_channel.connect(
                timeout=70.0,
                reconnect=True,
                self_deaf=True,
                self_mute=False
            )

        except asyncio.TimeoutError as error:

            logger.exception(
                "Таймаут подключения к голосовому каналу"
            )

            raise RuntimeError(
                "Не удалось подключиться к голосовому каналу.\n"
                "Discord не ответил вовремя.\n"
                "Проверь права Connect/Speak и настройки голосового канала."
            ) from error

        except discord.ClientException as error:

            logger.exception(
                "Ошибка подключения к voice"
            )

            raise RuntimeError(
                f"Ошибка подключения:\n{error}"
            ) from error

        except Exception:

            logger.exception(
                "Неизвестная ошибка подключения к voice"
            )

            raise

        player = MusicPlayer(
            voice_client,
            text_channel,
            self.bot.loop
        )

        self.players[guild_id] = player

        logger.info(
            f"Voice connected: {voice_channel.name}"
        )

        return player

    def get_player(
        self,
        guild_id: int
    ) -> MusicPlayer | None:
        """
        Получить активный плеер сервера.
        """

        return self.players.get(
            guild_id
        )

    async def disconnect(
        self,
        guild_id: int
    ) -> None:
        """
        Полностью отключить бота
        от голосового канала.
        """

        player = self.players.get(
            guild_id
        )

        if not player:
            return

        try:

            await player.shutdown()

        except Exception:

            logger.exception(
                "Ошибка shutdown player"
            )

        finally:

            self.players.pop(
                guild_id,
                None
            )

    async def shutdown(
        self
    ) -> None:
        """
        Завершение всех voice-соединений.
        """

        guilds = list(
            self.players.keys()
        )

        for guild_id in guilds:

            await self.disconnect(
                guild_id
            )
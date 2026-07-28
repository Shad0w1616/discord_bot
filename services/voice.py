from __future__ import annotations

from typing import Optional

import discord

from music.player import MusicPlayer

from music.exceptions import (
    VoiceConnectionError
)

from utils.logger import logger



class VoiceManager:
    """
    Управление голосовыми соединениями.

    Отвечает за:

    - подключение к VoiceChannel;
    - получение MusicPlayer;
    - хранение плееров серверов.

    Не отвечает за:

    - музыку;
    - очередь;
    - FFmpeg.
    """


    def __init__(self):

        self.players: dict[int, MusicPlayer] = {}



    # =====================================================
    # Получение плеера
    # =====================================================


    def get_player(
        self,
        guild_id: int
    ) -> Optional[MusicPlayer]:
        """
        Возвращает плеер сервера.

        Если плеер не создан —
        возвращает None.
        """


        return self.players.get(
            guild_id
        )



    def create_player(
        self,
        guild_id: int,
        voice_client: discord.VoiceClient
    ) -> MusicPlayer:
        """
        Создаёт новый MusicPlayer.
        """


        player = MusicPlayer(

            guild_id=guild_id,

            voice_client=voice_client

        )


        self.players[guild_id] = player


        logger.info(

            f"[{guild_id}] "
            "Создан новый MusicPlayer."

        )


        return player



    # =====================================================
    # Подключение
    # =====================================================


    async def connect(
        self,
        member: discord.Member
    ) -> MusicPlayer:
        """
        Подключает бота
        к каналу пользователя.

        Возвращает MusicPlayer.
        """


        if not member.voice:

            raise VoiceConnectionError(

                "Пользователь не находится "
                "в голосовом канале."

            )



        channel = member.voice.channel


        guild = member.guild



        existing_player = self.get_player(

            guild.id

        )


        # =============================================
        # Если уже есть соединение
        # =============================================


        if existing_player:


            if existing_player.voice_client.channel != channel:


                await existing_player.voice_client.move_to(

                    channel

                )


            return existing_player



        # =============================================
        # Создание подключения
        # =============================================


        try:


            voice_client = await channel.connect()



        except Exception as error:


            logger.exception(

                "Ошибка подключения Discord voice."

            )


            raise VoiceConnectionError(

                str(error)

            )



        player = self.create_player(

            guild_id=guild.id,

            voice_client=voice_client

        )



        return player



    # =====================================================
    # Отключение
    # =====================================================


    async def disconnect(
        self,
        guild_id: int
    ):
        """
        Полностью отключает бота
        от голосового канала.
        """


        player = self.players.get(

            guild_id

        )


        if not player:

            return



        await player.disconnect()



        del self.players[guild_id]



        logger.info(

            f"[{guild_id}] "
            "MusicPlayer удалён."

        )



    # =====================================================
    # Проверка состояния
    # =====================================================


    def has_player(
        self,
        guild_id: int
    ) -> bool:
        """
        Есть ли активный плеер.
        """


        return guild_id in self.players



    def get_active_players(
        self
    ) -> list[MusicPlayer]:
        """
        Все активные плееры.
        """


        return list(

            self.players.values()

        )



    async def shutdown(
        self
    ):
        """
        Корректное завершение работы.

        Отключает всех ботов
        от голосовых каналов.
        """


        for guild_id in list(

            self.players.keys()

        ):

            await self.disconnect(

                guild_id

            )
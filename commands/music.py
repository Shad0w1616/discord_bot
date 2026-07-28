from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.youtube import YoutubeService

from music.models import (
    Track,
    Playlist
)


from utils.embeds import (
    error_embed,
    success_embed,
    now_playing_embed,
    queue_embed,
    info_embed
)


from utils.logger import logger



class MusicCommands(
    commands.Cog
):
    """
    Slash-команды управления музыкой.
    """


    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot


        self.youtube = YoutubeService()



    # =====================================================
    # /notorious
    # =====================================================


    @app_commands.command(
        name="notorious",
        description=(
            "Добавить трек или плейлист "
            "в очередь"
        )
    )
    @app_commands.describe(

        query=(
            "Ссылка YouTube "
            "или поисковый запрос"
        )

    )
    async def notorious(
        self,
        interaction: discord.Interaction,
        query: str
    ):

        await interaction.response.defer()


        try:

            player = await self.bot.voice_manager.connect(

                interaction.user

            )
            player.on_track_start = self.track_started

            result = await self.youtube.resolve(

                query

            )


            # =========================================
            # Плейлист
            # =========================================


            if isinstance(
                result,
                Playlist
            ):


                tracks = result.tracks



                for track in tracks:

                    track.requester = interaction.user



                await player.enqueue_many(

                    tracks

                )



                await interaction.followup.send(

                    embed=success_embed(

                        f"Добавлено в очередь: "
                        f"**{len(tracks)}** треков"

                    )

                )



            # =========================================
            # Один трек
            # =========================================


            elif isinstance(
                result,
                Track
            ):


                result.requester = (
                    interaction.user
                )


                await player.enqueue(

                    result

                )


                await interaction.followup.send(

                    embed=now_playing_embed(

                        result.title

                    )

                )



            logger.info(

                f"{interaction.user} "
                f"добавил: {query}"

            )


        except Exception as error:


            logger.exception(

                "Ошибка команды notorious"

            )


            await interaction.followup.send(

                embed=error_embed(

                    str(error)

                )

            )



    # =====================================================
    # /sambovanie
    # =====================================================


    @app_commands.command(
        name="sambovanie",
        description=(
            "Поставить музыку "
            "на паузу или продолжить"
        )
    )
    async def sambovanie(
        self,
        interaction: discord.Interaction
    ):


        player = self.bot.voice_manager.get_player(

            interaction.guild.id

        )


        if not player:


            await interaction.response.send_message(

                embed=error_embed(

                    "Музыка сейчас не играет."

                )

            )

            return



        if player.paused:


            result = player.resume()


            message = (
                "▶️ Музыка продолжена."
            )


        else:


            result = player.pause()


            message = (
                "⏸ Музыка поставлена "
                "на паузу."
            )



        if result:


            await interaction.response.send_message(

                embed=success_embed(

                    message

                )

            )

        else:


            await interaction.response.send_message(

                embed=error_embed(

                    "Не удалось изменить состояние."

                )

            )



    # =====================================================
    # /next
    # =====================================================


    @app_commands.command(
        name="next",
        description=(
            "Пропустить текущий трек"
        )
    )
    async def next(
        self,
        interaction: discord.Interaction
    ):


        player = self.bot.voice_manager.get_player(

            interaction.guild.id

        )


        if not player:


            await interaction.response.send_message(

                embed=error_embed(

                    "Нет активного плеера."

                )

            )

            return



        result = await player.skip()



        if result:


            await interaction.response.send_message(

                embed=success_embed(

                    "Трек пропущен."

                )

            )


        else:


            await interaction.response.send_message(

                embed=error_embed(

                    "Сейчас ничего не играет."

                )

            )



    # =====================================================
    # /queue
    # =====================================================


    @app_commands.command(
        name="queue",
        description=(
            "Показать очередь"
        )
    )
    async def queue(
        self,
        interaction: discord.Interaction
    ):


        player = self.bot.voice_manager.get_player(

            interaction.guild.id

        )


        if not player:


            await interaction.response.send_message(

                embed=error_embed(

                    "Очередь пуста."

                )

            )

            return



        tracks = player.get_queue_preview(

            5

        )


        names = [

            track.title

            for track in tracks

        ]



        await interaction.response.send_message(

            embed=queue_embed(

                names

            )

        )



    # =====================================================
    # /stop
    # =====================================================


    @app_commands.command(
        name="stop",
        description=(
            "Остановить музыку"
        )
    )
    async def stop(
        self,
        interaction: discord.Interaction
    ):


        player = self.bot.voice_manager.get_player(

            interaction.guild.id

        )


        if not player:


            await interaction.response.send_message(

                embed=error_embed(

                    "Нет активного плеера."

                )

            )

            return



        await player.stop()



        await interaction.response.send_message(

            embed=success_embed(

                "Музыка остановлена."

            )

        )



async def setup(
    bot: commands.Bot
):
    """
    Подключение Cog.
    """


    await bot.add_cog(

        MusicCommands(

            bot

        )

    )
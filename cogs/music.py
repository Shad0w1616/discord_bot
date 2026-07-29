from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from utils.embeds import (
    success_embed,
    error_embed,
    queue_embed
)

from utils.logger import logger



class MusicCommands(commands.Cog):
    """
    Музыкальные slash-команды.
    """



    def __init__(
        self,
        bot
    ):

        self.bot = bot





    @app_commands.command(
        name="notorious",
        description="Добавить трек или плейлист"
    )
    async def notorious(
        self,
        interaction: discord.Interaction,
        query: str
    ):


        await interaction.response.defer()



        if not interaction.guild:


            await interaction.followup.send(

                embed=error_embed(

                    "Команда доступна только на сервере."

                )

            )

            return





        if not interaction.user.voice:


            await interaction.followup.send(

                embed=error_embed(

                    "Сначала зайдите в голосовой канал."

                )

            )

            return





        try:


            player = await self.bot.voice_manager.connect(

                interaction.user,

                interaction.channel

            )



            youtube = player.youtube



            if "list=" in query:


                playlist = await youtube.get_playlist(

                    query,

                    interaction.guild.id,

                    interaction.user

                )



                if playlist.count == 0:


                    await interaction.followup.send(

                        embed=error_embed(

                            "Плейлист пуст."

                        )

                    )

                    return



                await player.enqueue_many(

                    playlist.tracks

                )



                await interaction.followup.send(

                    embed=success_embed(

                        f"Добавлен плейлист:\n"
                        f"**{playlist.title}**\n"
                        f"Треков: {playlist.count}"

                    )

                )



            else:


                track = await youtube.get_track(

                    query,

                    interaction.guild.id,

                    interaction.user

                )



                await player.enqueue(

                    track

                )



                await interaction.followup.send(

                    embed=success_embed(

                        f"Добавлен:\n"
                        f"**{track.title}**"

                    )

                )





        except Exception as error:


            logger.exception(

                "Ошибка /notorious"

            )


            await interaction.followup.send(

                embed=error_embed(

                    f"Ошибка:\n{error}"

                )

            )





    @app_commands.command(
        name="sambovanie",
        description="Пауза или продолжение музыки"
    )
    async def sambovanie(
        self,
        interaction: discord.Interaction
    ):


        if not interaction.guild:


            await interaction.response.send_message(

                embed=error_embed(

                    "Команда доступна только на сервере."

                )

            )

            return





        player = self.bot.voice_manager.get_player(

            interaction.guild.id

        )



        if not player:


            await interaction.response.send_message(

                embed=error_embed(

                    "Музыка не запущена."

                )

            )

            return





        paused = player.toggle_pause()



        await interaction.response.send_message(

            embed=success_embed(

                "⏸️ Пауза"

                if paused

                else

                "▶️ Продолжено"

            )

        )





    @app_commands.command(
        name="next",
        description="Пропустить текущий трек"
    )
    async def next_track(
        self,
        interaction: discord.Interaction
    ):


        if not interaction.guild:


            await interaction.response.send_message(

                embed=error_embed(

                    "Команда доступна только на сервере."

                )

            )

            return





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



        await interaction.response.send_message(

            embed=success_embed(

                "Трек пропущен."

            )

            if result

            else

            error_embed(

                "Сейчас ничего не играет."

            )

        )





    @app_commands.command(
        name="queue",
        description="Показать очередь"
    )
    async def queue(
        self,
        interaction: discord.Interaction
    ):


        if not interaction.guild:


            await interaction.response.send_message(

                embed=error_embed(

                    "Команда доступна только на сервере."

                )

            )

            return





        player = self.bot.voice_manager.get_player(

            interaction.guild.id

        )



        if not player:


            await interaction.response.send_message(

                embed=queue_embed([])

            )

            return





        await interaction.response.send_message(

            embed=queue_embed(

                player.get_queue_preview()

            )

        )





async def setup(
    bot
):

    await bot.add_cog(

        MusicCommands(
            bot
        )

    )
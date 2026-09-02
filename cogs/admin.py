from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from utils.embeds import (
    success_embed,
    error_embed
)

from utils.logger import logger



class AdminCommands(commands.Cog):
    """
    Административные команды управления ботом.
    """



    def __init__(
        self,
        bot
    ):

        self.bot = bot





    @app_commands.command(
        name="stop",
        description="Остановить музыку и очистить очередь"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def stop(
        self,
        interaction: discord.Interaction
    ):


        if not interaction.guild:


            await interaction.response.send_message(

                embed=error_embed(

                    "Команда доступна только на сервере."

                ),

                ephemeral=True

            )

            return





        await interaction.response.defer()



        player = self.bot.voice_manager.get_player(

            interaction.guild.id

        )



        if not player:


            await interaction.followup.send(

                embed=error_embed(

                    "Бот не подключён к голосовому каналу."

                )

            )

            return





        await self.bot.voice_manager.disconnect(

            interaction.guild.id

        )



        await interaction.followup.send(

            embed=success_embed(

                "Музыка остановлена, бот отключён."

            )

        )





    @app_commands.command(
        name="clear",
        description="Очистить очередь"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def clear(
        self,
        interaction: discord.Interaction
    ):


        if not interaction.guild:


            await interaction.response.send_message(

                embed=error_embed(

                    "Команда доступна только на сервере."

                ),

                ephemeral=True

            )

            return





        player = self.bot.voice_manager.get_player(

            interaction.guild.id

        )



        if not player:


            await interaction.response.send_message(

                embed=error_embed(

                    "Активного плеера нет."

                ),

                ephemeral=True

            )

            return





        player.queue.clear()



        await interaction.response.send_message(

            embed=success_embed(

                "Очередь очищена."

            )

        )





    @app_commands.command(
        name="disconnect",
        description="Отключить бота от голосового канала"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def disconnect(
        self,
        interaction: discord.Interaction
    ):


        if not interaction.guild:


            await interaction.response.send_message(

                embed=error_embed(

                    "Команда доступна только на сервере."

                ),

                ephemeral=True

            )

            return





        await interaction.response.defer()



        await self.bot.voice_manager.disconnect(

            interaction.guild.id

        )



        await interaction.followup.send(

            embed=success_embed(

                "Бот отключён."

            )

        )





    # =====================================================
    # Ошибки прав
    # =====================================================


    @stop.error
    @clear.error
    @disconnect.error
    async def command_error(
        self,
        interaction: discord.Interaction,
        error
    ):


        if isinstance(

            error,

            app_commands.MissingPermissions

        ):


            await interaction.response.send_message(

                embed=error_embed(

                    "Недостаточно прав."

                ),

                ephemeral=True

            )

            return





        logger.exception(

            "Ошибка admin команды",

            exc_info=error

        )



        if interaction.response.is_done():


            await interaction.followup.send(

                embed=error_embed(

                    "Внутренняя ошибка."

                ),

                ephemeral=True

            )


        else:


            await interaction.response.send_message(

                embed=error_embed(

                    "Внутренняя ошибка."

                ),

                ephemeral=True

            )





async def setup(
    bot
):

    await bot.add_cog(

        AdminCommands(
            bot
        )

    )
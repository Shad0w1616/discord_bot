from __future__ import annotations

import discord

from discord import app_commands

from discord.ext import commands

from utils.embeds import (
    success_embed,
    error_embed,
    info_embed
)


from utils.logger import logger



class AdminCommands(
    commands.Cog
):
    """
    Административные slash-команды.
    """


    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot



    # =====================================================
    # Проверка прав администратора
    # =====================================================


    async def is_admin(
        self,
        interaction: discord.Interaction
    ) -> bool:
        """
        Проверка прав пользователя.
        """


        if not interaction.guild:

            return False


        member = interaction.user


        return member.guild_permissions.administrator



    # =====================================================
    # /disconnect
    # =====================================================


    @app_commands.command(
        name="disconnect",
        description=(
            "Отключить бота "
            "из голосового канала"
        )
    )
    async def disconnect(
        self,
        interaction: discord.Interaction
    ):


        if not await self.is_admin(
            interaction
        ):


            await interaction.response.send_message(

                embed=error_embed(

                    "Недостаточно прав."

                ),

                ephemeral=True

            )

            return



        guild_id = interaction.guild.id



        try:


            await self.bot.voice_manager.disconnect(

                guild_id

            )


            await interaction.response.send_message(

                embed=success_embed(

                    "Бот отключён "
                    "от голосового канала."

                )

            )


            logger.info(

                f"{interaction.user} "
                f"отключил бота "
                f"на сервере {guild_id}"

            )



        except Exception as error:


            logger.exception(

                "Ошибка disconnect"

            )


            await interaction.response.send_message(

                embed=error_embed(

                    str(error)

                )

            )



    # =====================================================
    # /botstatus
    # =====================================================


    @app_commands.command(
        name="botstatus",
        description=(
            "Показать состояние бота"
        )
    )
    async def botstatus(
        self,
        interaction: discord.Interaction
    ):


        uptime = self.bot.latency * 1000


        embed = info_embed(

            "Состояние бота"

        )


        embed.add_field(

            name="Имя",

            value=str(
                self.bot.user
            ),

            inline=False

        )


        embed.add_field(

            name="Ping",

            value=f"{uptime:.0f} ms",

            inline=False

        )


        embed.add_field(

            name="Серверов",

            value=str(
                len(self.bot.guilds)
            ),

            inline=False

        )


        await interaction.response.send_message(

            embed=embed

        )



    # =====================================================
    # /reload_music
    # =====================================================


    @app_commands.command(
        name="reload_music",
        description=(
            "Перезагрузить "
            "музыкальный модуль"
        )
    )
    async def reload_music(
        self,
        interaction: discord.Interaction
    ):


        if not await self.is_admin(
            interaction
        ):


            await interaction.response.send_message(

                embed=error_embed(

                    "Недостаточно прав."

                ),

                ephemeral=True

            )

            return



        await interaction.response.defer()



        try:


            await self.bot.reload_extension(

                "commands.music"

            )


            await interaction.followup.send(

                embed=success_embed(

                    "Музыкальный модуль "
                    "перезагружен."

                )

            )


            logger.info(

                "Music Cog перезагружен."

            )



        except Exception as error:


            logger.exception(

                "Ошибка reload_music"

            )


            await interaction.followup.send(

                embed=error_embed(

                    str(error)

                )

            )



async def setup(
    bot: commands.Bot
):
    """
    Подключение Cog.
    """


    await bot.add_cog(

        AdminCommands(

            bot

        )

    )
from __future__ import annotations

from dataclasses import replace

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import queue_embed
from utils.logger import logger


class PlaylistCommands(commands.GroupCog, group_name="playlist", group_description="Мои сохранённые плейлисты"):
    def __init__(self, bot):
        self.bot = bot

    async def begin(self, interaction):
        if not interaction.guild:
            raise ValueError("Команда доступна только на сервере.")
        await interaction.response.defer(ephemeral=True)

    async def store(self, interaction, action, name="", **kwargs):
        return await self.bot.playlists.execute(action, interaction.guild_id, interaction.user.id, name, **kwargs)

    @app_commands.command(name="create", description="Создать личный плейлист")
    async def create(self, interaction: discord.Interaction, name: str):
        await self.begin(interaction)
        await self.store(interaction, "create", name)
        await interaction.followup.send("Плейлист создан. Добавляйте музыку кнопкой «В плейлист» под треком.", ephemeral=True)

    @app_commands.command(name="list", description="Показать мои плейлисты")
    async def list_playlists(self, interaction: discord.Interaction):
        await self.begin(interaction)
        playlists = await self.store(interaction, "list")
        text = "\n".join(f"• {discord.utils.escape_markdown(n)} — {c} треков" for n, c in playlists)
        await interaction.followup.send(embed=discord.Embed(title="Мои плейлисты", description=text or "У вас пока нет плейлистов. Используйте /playlist create."),
                                        ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="show", description="Посмотреть треки сохранённого плейлиста")
    async def show(self, interaction: discord.Interaction, name: str, page: app_commands.Range[int, 1] = 1):
        await self.begin(interaction)
        tracks = await self.store(interaction, "get", name)
        if page > max(1, (len(tracks) + 9) // 10):
            raise ValueError("Такой страницы нет.")
        embed = queue_embed(tracks[(page - 1)*10:page*10], page=page, total=len(tracks))
        embed.title = f"Плейлист: {name[:50]}"
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="play", description="Добавить мой плейлист в обычную очередь")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.guild_id or i.user.id)
    async def play(self, interaction: discord.Interaction, name: str):
        await self.begin(interaction)
        tracks = await self.store(interaction, "get", name)
        if not tracks:
            raise ValueError("Плейлист пуст.")
        player = await self.bot.voice_manager.connect(interaction.user, interaction.channel)
        player.require_normal_mode()
        requested = [replace(t, requester_id=interaction.user.id,
                             requester_name=interaction.user.display_name) for t in tracks]
        added = await player.enqueue_many(requested)
        await interaction.followup.send(f"Добавлено в очередь: {added} из {len(tracks)} треков.", ephemeral=True)

    @app_commands.command(name="remove", description="Удалить трек из моего плейлиста по номеру")
    async def remove(self, interaction: discord.Interaction, name: str, position: app_commands.Range[int, 1]):
        await self.begin(interaction)
        await self.store(interaction, "remove", name, position=position)
        await interaction.followup.send("Трек удалён из плейлиста.", ephemeral=True)

    @app_commands.command(name="delete", description="Удалить мой плейлист (нужно confirm:true)")
    async def delete(self, interaction: discord.Interaction, name: str, confirm: bool = False):
        await self.begin(interaction)
        if not confirm:
            raise ValueError("Для удаления укажите confirm:true.")
        await self.store(interaction, "delete", name)
        await interaction.followup.send("Плейлист удалён.", ephemeral=True)

    async def cog_app_command_error(self, interaction, error):
        error = getattr(error, "original", error)
        if isinstance(error, (ValueError, RuntimeError)):
            message = str(error)
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = f"Повторите через {error.retry_after:.0f} сек."
        else:
            logger.error("Ошибка плейлиста", exc_info=(type(error), error, error.__traceback__))
            message = "Не удалось выполнить действие с плейлистом."
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(message, ephemeral=True)


async def setup(bot):
    await bot.add_cog(PlaylistCommands(bot))

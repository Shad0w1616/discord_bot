from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from settings import settings
from utils.embeds import error_embed, now_playing_embed, queue_embed, success_embed
from utils.logger import logger


class MusicCommands(commands.Cog):
    """Музыкальные slash-команды."""

    def __init__(self, bot) -> None:
        self.bot = bot

    def _player_for_control(self, interaction: discord.Interaction):
        if not interaction.guild:
            raise RuntimeError("Команда доступна только на сервере.")
        player = self.bot.voice_manager.get_player(interaction.guild.id)
        if not player or not player.voice_client.is_connected():
            raise RuntimeError("Бот не подключён к голосовому каналу.")
        member_channel = getattr(getattr(interaction.user, "voice", None), "channel", None)
        if not member_channel or member_channel.id != player.voice_client.channel.id:
            raise RuntimeError("Зайдите в голосовой канал бота для управления музыкой.")
        return player

    @app_commands.command(name="play", description="Добавить трек или плейлист")
    @app_commands.checks.cooldown(
        1,
        settings.PLAY_COOLDOWN_SECONDS,
        key=lambda interaction: interaction.guild_id or interaction.user.id,
    )
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        if not interaction.guild:
            await interaction.followup.send(embed=error_embed("Команда доступна только на сервере."))
            return
        if not getattr(interaction.user, "voice", None):
            await interaction.followup.send(embed=error_embed("Сначала зайдите в голосовой канал."))
            return

        existing = self.bot.voice_manager.get_player(interaction.guild.id)
        if existing and existing.voice_client.is_connected():
            user_channel = interaction.user.voice.channel
            if existing.voice_client.channel.id != user_channel.id:
                await interaction.followup.send(
                    embed=error_embed("Бот уже играет в другом голосовом канале.")
                )
                return

        try:
            player = await self.bot.voice_manager.connect(
                interaction.user,
                interaction.channel,
            )
            available = settings.MAX_QUEUE_SIZE - player.queue.size()
            if available <= 0:
                raise RuntimeError(
                    f"Очередь заполнена: максимум {settings.MAX_QUEUE_SIZE} треков."
                )

            if "list=" in query:
                playlist_limit = min(settings.MAX_PLAYLIST_SIZE, available)
                playlist = await player.youtube.get_playlist(
                    query,
                    interaction.guild.id,
                    interaction.user,
                    max_items=playlist_limit,
                )
                if playlist.count == 0:
                    raise RuntimeError("Плейлист пуст или недоступен.")
                added = await player.enqueue_many(playlist.tracks)
                await interaction.followup.send(
                    embed=success_embed(
                        f"Добавлен плейлист **{playlist.title}**\nТреков: {added}"
                    )
                )
            else:
                track = await player.youtube.get_track(
                    query,
                    interaction.guild.id,
                    interaction.user,
                )
                await player.enqueue(track)
                await interaction.followup.send(
                    embed=success_embed(f"Добавлен: **{track.title}**")
                )
        except Exception as error:
            logger.exception("Ошибка /play")
            await interaction.followup.send(embed=error_embed(str(error)))

    @play.error
    async def play_error(self, interaction: discord.Interaction, error) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                embed=error_embed(f"Подождите {error.retry_after:.1f} сек. перед новым запросом."),
                ephemeral=True,
            )
            return
        raise error

    @app_commands.command(name="pause", description="Пауза или продолжение музыки")
    async def pause(self, interaction: discord.Interaction) -> None:
        try:
            player = self._player_for_control(interaction)
            paused = player.toggle_pause()
            if paused is None:
                await interaction.response.send_message(embed=error_embed("Сейчас ничего не играет."))
            else:
                await interaction.response.send_message(
                    embed=success_embed("⏸️ Пауза" if paused else "▶️ Продолжено")
                )
        except RuntimeError as error:
            await interaction.response.send_message(embed=error_embed(str(error)), ephemeral=True)

    @app_commands.command(name="next", description="Пропустить текущий трек")
    async def next_track(self, interaction: discord.Interaction) -> None:
        try:
            player = self._player_for_control(interaction)
            result = await player.skip()
            embed = success_embed("Трек пропущен.") if result else error_embed("Сейчас ничего не играет.")
            await interaction.response.send_message(embed=embed)
        except RuntimeError as error:
            await interaction.response.send_message(embed=error_embed(str(error)), ephemeral=True)

    @app_commands.command(name="queue", description="Показать очередь")
    @app_commands.describe(page="Номер страницы")
    async def queue(self, interaction: discord.Interaction, page: app_commands.Range[int, 1] = 1) -> None:
        if not interaction.guild:
            await interaction.response.send_message(embed=error_embed("Команда доступна только на сервере."))
            return
        player = self.bot.voice_manager.get_player(interaction.guild.id)
        if not player:
            stored = await self.bot.voice_manager.storage.load(interaction.guild.id)
            total = len(stored)
            page_size = 10
            pages = max(1, (total + page_size - 1) // page_size)
            if page > pages:
                await interaction.response.send_message(
                    embed=error_embed(f"В сохранённой очереди только {pages} стр."),
                    ephemeral=True,
                )
                return
            start = (page - 1) * page_size
            await interaction.response.send_message(
                embed=queue_embed(
                    stored[start:start + page_size],
                    page=page,
                    page_size=page_size,
                    total=total,
                )
            )
            return
        page_size = 10
        total = player.queue.size()
        pages = max(1, (total + page_size - 1) // page_size)
        if page > pages:
            await interaction.response.send_message(
                embed=error_embed(f"В очереди только {pages} стр."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=queue_embed(
                player.queue.page(page, page_size),
                current=player.current,
                page=page,
                page_size=page_size,
                total=total,
            )
        )

    @app_commands.command(name="nowplaying", description="Показать текущий трек")
    async def now_playing(self, interaction: discord.Interaction) -> None:
        player = self.bot.voice_manager.get_player(interaction.guild.id) if interaction.guild else None
        if not player or not player.current:
            await interaction.response.send_message(embed=error_embed("Сейчас ничего не играет."))
            return
        await interaction.response.send_message(embed=now_playing_embed(player.current))

    @app_commands.command(name="remove", description="Удалить трек из очереди")
    async def remove(self, interaction: discord.Interaction, position: app_commands.Range[int, 1]) -> None:
        try:
            player = self._player_for_control(interaction)
            track = await player.remove(position)
            await interaction.response.send_message(embed=success_embed(f"Удалён: **{track.title}**"))
        except (RuntimeError, IndexError) as error:
            await interaction.response.send_message(embed=error_embed(str(error)), ephemeral=True)

    @app_commands.command(name="shuffle", description="Перемешать очередь")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        try:
            player = self._player_for_control(interaction)
            count = await player.shuffle()
            if count < 2:
                raise RuntimeError("Для перемешивания нужно хотя бы два трека в очереди.")
            await interaction.response.send_message(embed=success_embed(f"Перемешано треков: {count}"))
        except RuntimeError as error:
            await interaction.response.send_message(embed=error_embed(str(error)), ephemeral=True)

    @app_commands.command(name="repeat", description="Включить или выключить повтор текущего трека")
    async def repeat(self, interaction: discord.Interaction, enabled: bool) -> None:
        try:
            player = self._player_for_control(interaction)
            await player.set_repeat(enabled)
            await interaction.response.send_message(
                embed=success_embed("Повтор включён." if enabled else "Повтор выключен.")
            )
        except RuntimeError as error:
            await interaction.response.send_message(embed=error_embed(str(error)), ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(MusicCommands(bot))

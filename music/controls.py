from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import replace

import discord

from utils.embeds import error_embed, queue_embed, success_embed
from utils.logger import logger

if TYPE_CHECKING:
    from music.player import MusicPlayer


class PlayerControls(discord.ui.View):
    """Only the current track's message may control its player."""

    def __init__(self, player: MusicPlayer) -> None:
        super().__init__(timeout=None)
        self.player = player
        self.active = True
        self.sync_buttons()

    def sync_buttons(self) -> None:
        player = self.player
        self.back.disabled = not bool(player.history)
        self.pause.label = "Продолжить" if player.voice_client.is_paused() else "Пауза"
        self.pause.emoji = "▶️" if player.voice_client.is_paused() else "⏸️"
        self.repeat.label = "Повтор: вкл" if player.repeat_enabled else "Повтор: выкл"
        self.repeat.style = discord.ButtonStyle.success if player.repeat_enabled else discord.ButtonStyle.secondary
        self.shuffle.disabled = player.wave_active or player.queue.size() < 2
        self.remove.disabled = player.wave_active or player.queue.empty()
        self.clear.disabled = player.wave_active or player.queue.empty()
        self.stop_playback.label = "Остановить волну" if player.wave_active else "Стоп"

    def check_access(self, interaction: discord.Interaction, *, admin=False) -> None:
        if (not self.active or self.player.panel_view is not self
                or self.player._shutting_down or self.player.current is None
                or not self.player.voice_client.is_connected()):
            raise RuntimeError("Эта панель устарела. Используйте панель текущего трека.")
        channel = getattr(getattr(interaction.user, "voice", None), "channel", None)
        if (interaction.guild_id != self.player.guild_id or channel is None
                or channel.id != self.player.voice_client.channel.id):
            raise RuntimeError("Зайдите в голосовой канал бота для управления музыкой.")
        if admin and not interaction.user.guild_permissions.administrator:
            raise RuntimeError("Для остановки обычного плеера и очистки очереди нужны права администратора.")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            self.check_access(interaction)
            return True
        except RuntimeError as error:
            await interaction.response.send_message(embed=error_embed(str(error)), ephemeral=True)
            return False

    async def run_action(self, interaction: discord.Interaction, action: str) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            self.check_access(interaction, admin=(action in {"clear", "disconnect"}
                                                or action == "stop" and not self.player.wave_active))
            player = self.player
            if action == "back":
                await player.previous()
                message = "Возвращаю предыдущий трек."
            elif action == "pause":
                paused = player.toggle_pause()
                if paused is None:
                    raise RuntimeError("Сейчас ничего не играет.")
                await player.refresh_panel()
                message = "Пауза." if paused else "Воспроизведение продолжено."
            elif action == "next":
                if not await player.skip():
                    raise RuntimeError("Сейчас ничего не играет.")
                message = "Трек пропущен."
            elif action == "repeat":
                await player.set_repeat(not player.repeat_enabled)
                message = "Повтор включён." if player.repeat_enabled else "Повтор выключен."
            elif action == "shuffle":
                await player.shuffle()
                message = "Очередь перемешана."
            elif action == "clear":
                await player.clear_queue()
                message = "Очередь очищена."
            elif action == "stop" and player.wave_active:
                await player.stop_wave()
                message = "Волна остановлена."
            else:
                await player.shutdown()
                message = "Музыка остановлена, бот отключён."
            await interaction.followup.send(embed=success_embed(message), ephemeral=True)
        except (RuntimeError, IndexError) as error:
            await interaction.followup.send(embed=error_embed(str(error)), ephemeral=True)

    @discord.ui.button(label="Назад", emoji="⏮️", row=0)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.run_action(interaction, "back")

    @discord.ui.button(label="Пауза", emoji="⏸️", style=discord.ButtonStyle.primary, row=0)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.run_action(interaction, "pause")

    @discord.ui.button(label="Вперёд", emoji="⏭️", row=0)
    async def next_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.run_action(interaction, "next")

    @discord.ui.button(label="Повтор: выкл", emoji="🔂", row=0)
    async def repeat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.run_action(interaction, "repeat")

    @discord.ui.button(label="Очередь", emoji="📋", row=1)
    async def queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        tracks = self.player.queue.all()
        if self.player.wave:
            wave = self.player.wave
            tracks = list(wave.pending)[:max(0, wave.limit - wave.completed - bool(self.player.current))]
        embed = queue_embed(tracks[:10], current=self.player.current, total=len(tracks))
        embed.set_footer(text=f"В очереди: {len(tracks)} • Все страницы: /queue")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Перемешать", emoji="🔀", row=1)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.run_action(interaction, "shuffle")

    @discord.ui.button(label="Удалить трек", emoji="➖", row=1)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveTrackModal(self))

    @discord.ui.button(label="Очистить очередь", emoji="🧹", row=1)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.run_action(interaction, "clear")

    @discord.ui.button(label="Стоп", emoji="⏹️", style=discord.ButtonStyle.danger, row=2)
    async def stop_playback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.run_action(interaction, "stop")

    @discord.ui.button(label="В плейлист", emoji="💾", style=discord.ButtonStyle.success, row=2)
    async def save_playlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.check_access(interaction)
        await interaction.response.send_modal(SaveTrackModal(
            interaction.client.playlists, self.player.guild_id, interaction.user.id,
            replace(self.player.current),
        ))

    @discord.ui.button(label="Отключить", emoji="🔌", row=2)
    async def disconnect(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.run_action(interaction, "disconnect")

    async def on_error(self, interaction, error, item) -> None:
        logger.error("Ошибка панели плеера", exc_info=(type(error), error, error.__traceback__))
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(embed=error_embed("Не удалось выполнить действие."), ephemeral=True)


class RemoveTrackModal(discord.ui.Modal, title="Удалить трек из очереди"):
    position = discord.ui.TextInput(label="Номер трека из /queue", max_length=5)

    def __init__(self, panel: PlayerControls):
        super().__init__(timeout=120)
        self.panel = panel
        self.snapshot = panel.player.queue.all()

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            self.panel.check_access(interaction)
            position = int(self.position.value)
            current = self.panel.player.queue.all()
            if (position < 1 or position > len(self.snapshot) or position > len(current)
                    or current[position - 1] is not self.snapshot[position - 1]):
                raise RuntimeError("Очередь изменилась или номер неверен. Откройте удаление заново.")
            track = await self.panel.player.remove(position)
            await interaction.followup.send(embed=success_embed(f"Удалён: **{track.title}**"), ephemeral=True)
        except (RuntimeError, IndexError, ValueError) as error:
            message = "Введите целый номер трека." if isinstance(error, ValueError) else str(error)
            await interaction.followup.send(embed=error_embed(message), ephemeral=True)

    async def on_error(self, interaction, error) -> None:
        await self.panel.on_error(interaction, error, None)


class SaveTrackModal(discord.ui.Modal, title="Сохранить трек в мой плейлист"):
    name = discord.ui.TextInput(label="Название (новый плейлист создастся сам)", min_length=1, max_length=50)

    def __init__(self, store, guild_id, user_id, track):
        super().__init__(timeout=180)
        self.store, self.guild_id, self.user_id, self.track = store, guild_id, user_id, track

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild_id != self.guild_id or interaction.user.id != self.user_id:
            await interaction.followup.send("Эта форма принадлежит другому пользователю.", ephemeral=True)
            return
        try:
            await self.store.execute("add", self.guild_id, self.user_id, self.name.value, track=self.track)
            await interaction.followup.send(f"Сохранён трек: {self.track.title[:200]}",
                                            ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        except ValueError as error:
            await interaction.followup.send(str(error), ephemeral=True)

    async def on_error(self, interaction, error):
        logger.error("Ошибка сохранения плейлиста", exc_info=(type(error), error, error.__traceback__))
        await interaction.followup.send("Не удалось сохранить трек. Попробуйте позже.", ephemeral=True)

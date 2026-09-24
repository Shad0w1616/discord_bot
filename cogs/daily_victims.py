from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

import discord
from discord import app_commands
from discord.ext import commands, tasks

from settings import settings
from utils.embeds import error_embed, success_embed
from utils.logger import logger


MSK = timezone(timedelta(hours=3), name="MSK")
CATEGORIES = (
    "Борец дня",
    "Я бы поставил ему десятку дня",
    "Пал Лаич дня",
    "Сосальщик дня",
    "Дима Крутиков дня",
    "Дася Вася Братва дня",
)


def choose_members(members: Sequence, count: int = len(CATEGORIES)) -> list:
    """Выбирает участников без повторов, когда людей достаточно."""
    if not members:
        return []
    generator = random.SystemRandom()
    if len(members) >= count:
        return generator.sample(list(members), count)
    return [generator.choice(members) for _ in range(count)]


def build_message(members: Sequence) -> str:
    lines = ["## 🎪 Жертвы движухи"]
    lines.extend(
        f"**{category}** — {member.mention}"
        for category, member in zip(CATEGORIES, members)
    )
    return "\n".join(lines)


class DailyVictimsStorage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    async def configure(self, guild_id: int, channel_id: int) -> None:
        async with self._lock:
            data = self._read()
            guild = data.setdefault(str(guild_id), {})
            guild["channel_id"] = channel_id
            self._write(data)

    async def disable(self, guild_id: int) -> None:
        async with self._lock:
            data = self._read()
            data.pop(str(guild_id), None)
            self._write(data)

    async def all(self) -> dict[str, dict]:
        async with self._lock:
            return self._read()

    async def is_sent(self, guild_id: int, date: str) -> bool:
        async with self._lock:
            guild = self._read().get(str(guild_id), {})
            return guild.get("last_sent") == date

    async def mark_sent(self, guild_id: int, date: str) -> None:
        async with self._lock:
            data = self._read()
            guild = data.get(str(guild_id))
            if guild:
                guild["last_sent"] = date
                self._write(data)

    def _read(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            logger.exception("Не удалось прочитать настройки рубрики")
            return {}

    def _write(self, data: dict[str, dict]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.path)
        except OSError:
            logger.exception("Не удалось сохранить настройки рубрики")


class DailyVictims(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.storage = DailyVictimsStorage(settings.DAILY_VICTIMS_STATE_PATH)

    async def cog_load(self) -> None:
        self.daily_check.start()

    async def cog_unload(self) -> None:
        self.daily_check.cancel()

    async def _eligible_members(self, guild: discord.Guild) -> list[discord.Member]:
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)
            except (discord.HTTPException, discord.ClientException):
                logger.exception("Не удалось загрузить участников guild=%s", guild.id)
        return [member for member in guild.members if not member.bot]

    async def _send_rubric(
        self,
        guild: discord.Guild,
        channel: discord.abc.Messageable,
    ) -> None:
        eligible = await self._eligible_members(guild)
        selected = choose_members(eligible)
        if not selected:
            raise RuntimeError("На сервере нет подходящих участников.")
        await channel.send(
            build_message(selected),
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False,
            ),
        )

    @tasks.loop(minutes=1)
    async def daily_check(self) -> None:
        now = datetime.now(MSK)
        if now.hour < 8:
            return

        today = now.date().isoformat()
        for guild_id, config in (await self.storage.all()).items():
            if config.get("last_sent") == today:
                continue
            try:
                parsed_guild_id = int(guild_id)
            except ValueError:
                logger.warning("Некорректный guild_id в настройках рубрики: %s", guild_id)
                continue
            guild = self.bot.get_guild(parsed_guild_id)
            channel = self.bot.get_channel(config.get("channel_id", 0))
            if not guild or not channel:
                logger.warning("Канал рубрики недоступен guild=%s", guild_id)
                continue
            try:
                await self._send_rubric(guild, channel)
                await self.storage.mark_sent(guild.id, today)
                logger.info("Рубрика отправлена guild=%s channel=%s", guild.id, channel.id)
            except (discord.HTTPException, RuntimeError):
                logger.exception("Не удалось отправить рубрику guild=%s", guild_id)

    @daily_check.before_loop
    async def before_daily_check(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="victims_setup",
        description="Настроить канал ежедневной рубрики «Жертвы движухи»",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_daily(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                embed=error_embed("Команда доступна только на сервере."),
                ephemeral=True,
            )
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                embed=error_embed("Выберите обычный текстовый канал."),
                ephemeral=True,
            )
            return
        await self.storage.configure(interaction.guild.id, target.id)
        await interaction.response.send_message(
            embed=success_embed(
                f"Рубрика будет выходить в {target.mention} ежедневно после 08:00 МСК."
            )
        )

    @app_commands.command(name="victims", description="Опубликовать «Жертвы движухи» сейчас")
    @app_commands.checks.cooldown(
        1,
        300.0,
        key=lambda interaction: interaction.guild_id or interaction.user.id,
    )
    async def victims_now(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not interaction.channel:
            await interaction.response.send_message(
                embed=error_embed("Команда доступна только на сервере."),
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        try:
            await self._send_rubric(interaction.guild, interaction.channel)
            await self.storage.mark_sent(
                interaction.guild.id,
                datetime.now(MSK).date().isoformat(),
            )
            await interaction.followup.send(
                embed=success_embed("Рубрика опубликована."),
                ephemeral=True,
            )
        except RuntimeError as error:
            await interaction.followup.send(embed=error_embed(str(error)), ephemeral=True)

    @app_commands.command(name="victims_disable", description="Отключить ежедневную рубрику")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_daily(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                embed=error_embed("Команда доступна только на сервере."),
                ephemeral=True,
            )
            return
        await self.storage.disable(interaction.guild.id)
        await interaction.response.send_message(embed=success_embed("Рубрика отключена."))

    async def cog_app_command_error(self, interaction: discord.Interaction, error) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "Для этой команды нужны права администратора."
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = f"Повторить рубрику можно через {error.retry_after:.0f} сек."
        else:
            logger.exception("Ошибка команды рубрики", exc_info=error)
            message = "Не удалось выполнить команду."
        if interaction.response.is_done():
            await interaction.followup.send(embed=error_embed(message), ephemeral=True)
        else:
            await interaction.response.send_message(embed=error_embed(message), ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(DailyVictims(bot))

from typing import Iterable

import discord

from config import settings


SUCCESS_COLOR = discord.Color.green()

ERROR_COLOR = discord.Color.red()

WARNING_COLOR = discord.Color.orange()

INFO_COLOR = discord.Color.blurple()

def base_embed(
    title: str,
    description: str = "",
    color: discord.Color = INFO_COLOR
) -> discord.Embed:

    embed = discord.Embed(

        title=title,

        description=description,

        color=color
    )

    return embed
def error_embed(
    message: str
) -> discord.Embed:

    return base_embed(

        title="❌ Ошибка",

        description=message,

        color=ERROR_COLOR
    )
def success_embed(
    message: str
) -> discord.Embed:

    return base_embed(

        title="✅ Готово",

        description=message,

        color=SUCCESS_COLOR
    )
def info_embed(
    message: str
) -> discord.Embed:

    return base_embed(

        title="ℹ Информация",

        description=message,

        color=INFO_COLOR
    )
def now_playing_embed(
    title: str
) -> discord.Embed:

    embed = discord.Embed(

        title="🎵 Сейчас играет",

        color=SUCCESS_COLOR
    )

    embed.add_field(

        name="Трек",

        value=title,

        inline=False
    )

    return embed
def queue_embed(
    tracks: Iterable[str]
) -> discord.Embed:

    embed = discord.Embed(

        title="📋 Очередь",

        color=INFO_COLOR
    )

    tracks = list(tracks)

    if not tracks:

        embed.description = "Очередь пуста."

        return embed

    description = []

    for index, title in enumerate(
        tracks[:settings.MAX_QUEUE_PREVIEW],
        start=1
    ):

        description.append(
            f"**{index}.** {title}"
        )

    embed.description = "\n".join(
        description
    )

    if len(tracks) > settings.MAX_QUEUE_PREVIEW:

        embed.set_footer(

            text=(
                f"И ещё "
                f"{len(tracks)-settings.MAX_QUEUE_PREVIEW} "
                f"трек(ов)"
            )
        )

    return embed
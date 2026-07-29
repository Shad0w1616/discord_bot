from __future__ import annotations

from collections.abc import Iterable

import discord

from music.models import Track



def success_embed(
    message: str
) -> discord.Embed:
    """
    Сообщение об успешном выполнении.
    """

    return discord.Embed(

        description=message,

        color=discord.Color.green()

    )





def error_embed(
    message: str
) -> discord.Embed:
    """
    Сообщение об ошибке.
    """

    return discord.Embed(

        description=message,

        color=discord.Color.red()

    )





def info_embed(
    message: str
) -> discord.Embed:
    """
    Информационное сообщение.
    """

    return discord.Embed(

        description=message,

        color=discord.Color.blue()

    )





def queue_embed(
    tracks: Iterable[Track]
) -> discord.Embed:
    """
    Формирует embed с очередью треков.
    """

    embed = discord.Embed(

        title="Очередь",

        color=discord.Color.blurple()

    )



    tracks = list(
        tracks
    )



    if not tracks:


        embed.description = (
            "Очередь пуста."
        )


        return embed





    lines = []



    for index, track in enumerate(

        tracks,

        start=1

    ):


        lines.append(

            f"**{index}.** "
            f"{track.title} "
            f"({track.duration_formatted})"

        )



    embed.description = "\n".join(
        lines
    )


    return embed





def now_playing_embed(
    track: Track
) -> discord.Embed:
    """
    Embed текущего трека.
    """

    embed = discord.Embed(

        title="Сейчас играет",

        description=(

            f"**{track.title}**\n"

            f"Длительность: "
            f"`{track.duration_formatted}`"

        ),

        color=discord.Color.gold()

    )



    if track.thumbnail:


        embed.set_thumbnail(

            url=track.thumbnail

        )



    return embed
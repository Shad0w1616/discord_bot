from __future__ import annotations

from collections.abc import Iterable

import discord

from music.models import Track


def success_embed(message: str) -> discord.Embed:
    return discord.Embed(description=message, color=discord.Color.green())


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(description=message, color=discord.Color.red())


def info_embed(message: str) -> discord.Embed:
    return discord.Embed(description=message, color=discord.Color.blue())


def queue_embed(
    tracks: Iterable[Track],
    *,
    current: Track | None = None,
    page: int = 1,
    page_size: int = 10,
    total: int | None = None,
) -> discord.Embed:
    tracks = list(tracks)
    embed = discord.Embed(title="Очередь", color=discord.Color.blurple())
    lines: list[str] = []
    if current:
        lines.append(f"▶️ **{current.title}** (`{current.duration_formatted}`)\n")
    start = (page - 1) * page_size
    for offset, track in enumerate(tracks, start=start + 1):
        requester = f" — {track.requester_name}" if track.requester_name else ""
        lines.append(
            f"**{offset}.** {track.title} (`{track.duration_formatted}`){requester}"
        )
    if not lines:
        embed.description = "Очередь пуста."
    else:
        embed.description = "\n".join(lines)
    if total is not None:
        pages = max(1, (total + page_size - 1) // page_size)
        embed.set_footer(text=f"Страница {page}/{pages} • В очереди: {total}")
    return embed


def now_playing_embed(track: Track) -> discord.Embed:
    requester = f"\nДобавил: {track.requester_name}" if track.requester_name else ""
    embed = discord.Embed(
        title="Сейчас играет",
        description=(
            f"**{track.title}**\n"
            f"Длительность: `{track.duration_formatted}`{requester}"
        ),
        color=discord.Color.gold(),
        url=track.url,
    )
    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    return embed

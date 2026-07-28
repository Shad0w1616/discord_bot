from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import discord


@dataclass(slots=True)
class Track:
    """
    Музыкальный трек.
    """

    title: str

    webpage_url: str

    stream_url: Optional[str] = None

    duration: Optional[int] = None

    uploader: Optional[str] = None

    thumbnail: Optional[str] = None

    requester: Optional[discord.Member] = None

    added_at: datetime = field(
        default_factory=datetime.utcnow
    )

    def __str__(self) -> str:

        return self.title


@dataclass(slots=True)
class Playlist:
    """
    YouTube-плейлист.
    """

    title: str

    tracks: list[Track]

    uploader: Optional[str] = None

    webpage_url: Optional[str] = None

    thumbnail: Optional[str] = None

    def __len__(self) -> int:

        return len(self.tracks)

    def __iter__(self):

        return iter(self.tracks)


@dataclass(slots=True)
class QueueItem:
    """
    Элемент очереди.
    """

    track: Track

    requester: discord.Member

    position: int = 0


@dataclass(slots=True)
class GuildState:
    """
    Состояние музыкального проигрывателя
    для одного Discord-сервера.
    """

    guild_id: int

    current_track: Optional[Track] = None

    paused: bool = False

    loop: bool = False

    volume: float = 1.0

    last_activity: datetime = field(
        default_factory=datetime.utcnow
    )

    def touch(self):

        self.last_activity = datetime.utcnow()
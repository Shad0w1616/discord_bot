from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional



@dataclass(slots=True)
class Track:
    """
    Модель одного музыкального трека.
    """

    title: str

    url: str

    guild_id: int

    duration: Optional[int] = None

    thumbnail: Optional[str] = None

    requester_id: Optional[int] = None

    requester_name: Optional[str] = None

    added_at: datetime = field(
        default_factory=datetime.utcnow
    )



    @property
    def duration_formatted(
        self
    ) -> str:
        """
        Возвращает длительность
        в формате MM:SS.
        """

        if self.duration is None:

            return "unknown"



        minutes = self.duration // 60

        seconds = self.duration % 60


        return (
            f"{minutes}:{seconds:02d}"
        )



    def set_requester(
        self,
        user
    ) -> None:
        """
        Сохраняет пользователя,
        который добавил трек.
        """

        self.requester_id = user.id


        self.requester_name = (

            user.display_name

            or user.name

        )





@dataclass(slots=True)
class Playlist:
    """
    Модель YouTube плейлиста.
    """

    title: str

    tracks: list[Track] = field(
        default_factory=list
    )



    @property
    def count(
        self
    ) -> int:
        """
        Количество треков.
        """

        return len(
            self.tracks
        )



    def add_track(
        self,
        track: Track
    ) -> None:
        """
        Добавляет один трек.
        """

        self.tracks.append(
            track
        )



    def add_tracks(
        self,
        tracks: list[Track]
    ) -> None:
        """
        Добавляет список треков.
        """

        self.tracks.extend(
            tracks
        )
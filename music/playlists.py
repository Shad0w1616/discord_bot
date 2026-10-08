from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from music.models import Track


class PlaylistStore:
    """Personal playlists scoped to a guild; each change is a SQLite transaction."""

    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def validate_name(name: str) -> str:
        name = " ".join(name.split())
        if not 1 <= len(name) <= 50:
            raise ValueError("Название плейлиста должно содержать от 1 до 50 символов.")
        return name

    async def execute(self, action: str, guild_id: int, user_id: int,
                      name: str = "", track: Track | None = None, position: int = 0):
        if action != "list":
            name = self.validate_name(name)
        return await asyncio.to_thread(self._execute, action, guild_id, user_id, name, track, position)

    def _execute(self, action, guild_id, user_id, name, track, position):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15)
        try:
            connection.execute("""CREATE TABLE IF NOT EXISTS playlists (
                guild TEXT NOT NULL, owner TEXT NOT NULL, key TEXT NOT NULL,
                name TEXT NOT NULL, tracks TEXT NOT NULL,
                PRIMARY KEY (guild, owner, key))""")
            connection.execute("BEGIN IMMEDIATE")
            scope = (str(guild_id), str(user_id))
            key = (*scope, name.casefold())
            if action == "list":
                return [(n, len(json.loads(t))) for n, t in connection.execute(
                    "SELECT name, tracks FROM playlists WHERE guild=? AND owner=? ORDER BY name", scope)]
            row = connection.execute(
                "SELECT name, tracks FROM playlists WHERE guild=? AND owner=? AND key=?", key).fetchone()
            if row is None:
                if action not in {"create", "add"}:
                    raise ValueError("Такого плейлиста у вас нет.")
                count = connection.execute(
                    "SELECT COUNT(*) FROM playlists WHERE guild=? AND owner=?", scope).fetchone()[0]
                if count >= 25:
                    raise ValueError("Можно создать не больше 25 плейлистов на сервере.")
                tracks = []
            else:
                name, payload = row
                tracks = json.loads(payload)
                if action == "create":
                    raise ValueError("Плейлист с таким названием уже существует.")
            if action == "get":
                result = []
                for item in tracks:
                    item["added_at"] = datetime.fromisoformat(item["added_at"])
                    result.append(Track(**item))
                return result
            if action == "delete":
                connection.execute("DELETE FROM playlists WHERE guild=? AND owner=? AND key=?", key)
            elif action in {"add", "create", "remove"}:
                if action == "add":
                    if track is None:
                        raise ValueError("Нет трека для сохранения.")
                    if any(t["url"] == track.url for t in tracks):
                        raise ValueError("Этот трек уже есть в плейлисте.")
                    if len(tracks) >= 200:
                        raise ValueError("В плейлисте уже 200 треков.")
                    item = asdict(track)
                    item["added_at"] = track.added_at.isoformat()
                    tracks.append(item)
                elif action == "remove":
                    if not 1 <= position <= len(tracks):
                        raise ValueError("Такой позиции в плейлисте нет.")
                    tracks.pop(position - 1)
                connection.execute("INSERT OR REPLACE INTO playlists VALUES (?, ?, ?, ?, ?)",
                                   (*key, name, json.dumps(tracks, ensure_ascii=False)))
            else:
                raise ValueError("Неизвестная операция.")
            connection.commit()
            return len(tracks)
        finally:
            connection.close()

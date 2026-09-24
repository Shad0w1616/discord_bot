from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from music.models import Track
from utils.logger import logger


class QueueStorage:
    """Хранит очереди между перезапусками процесса."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    async def load(self, guild_id: int) -> list[Track]:
        async with self._lock:
            data = self._read()

        tracks = []
        for item in data.get(str(guild_id), []):
            try:
                if isinstance(item.get("added_at"), str):
                    item["added_at"] = datetime.fromisoformat(item["added_at"])
                tracks.append(Track(**item))
            except (TypeError, ValueError):
                logger.warning("Пропущена повреждённая запись очереди guild=%s", guild_id)
        return tracks

    async def save(self, guild_id: int, tracks: list[Track]) -> None:
        async with self._lock:
            data = self._read()
            if tracks:
                serialized = []
                for track in tracks:
                    item = asdict(track)
                    item["added_at"] = track.added_at.isoformat()
                    serialized.append(item)
                data[str(guild_id)] = serialized
            else:
                data.pop(str(guild_id), None)
            try:
                self._write(data)
            except OSError:
                logger.exception("Не удалось сохранить очередь guild=%s", guild_id)

    def _read(self) -> dict[str, list[dict]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Не удалось прочитать сохранённые очереди")
            return {}

    def _write(self, data: dict[str, list[dict]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

from __future__ import annotations

import random
from collections import deque
from typing import Optional

from music.models import Track


class MusicQueue:
    """Очередь треков одного Discord-сервера."""

    def __init__(self) -> None:
        self._items: deque[Track] = deque()

    def add(self, track: Track) -> None:
        self._items.append(track)

    def add_first(self, track: Track) -> None:
        self._items.appendleft(track)

    def add_many(self, tracks: list[Track]) -> None:
        self._items.extend(tracks)

    def get_next(self) -> Optional[Track]:
        return self._items.popleft() if self._items else None

    def peek(self) -> Optional[Track]:
        return self._items[0] if self._items else None

    def page(self, page: int = 1, page_size: int = 10) -> list[Track]:
        start = (page - 1) * page_size
        return list(self._items)[start:start + page_size]

    def all(self) -> list[Track]:
        return list(self._items)

    def size(self) -> int:
        return len(self._items)

    def empty(self) -> bool:
        return not self._items

    def remove(self, position: int) -> Track:
        if position < 1 or position > len(self._items):
            raise IndexError("Такой позиции в очереди нет.")

        items = list(self._items)
        track = items.pop(position - 1)
        self._items = deque(items)
        return track

    def shuffle(self) -> None:
        items = list(self._items)
        random.shuffle(items)
        self._items = deque(items)

    def clear(self) -> None:
        self._items.clear()

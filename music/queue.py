from __future__ import annotations

from collections import deque
from typing import Optional

from music.models import Track



class MusicQueue:
    """
    Потокобезопасная логика очереди треков.

    Очередь принадлежит одному MusicPlayer
    конкретного Discord сервера.
    """



    def __init__(
        self
    ):

        self._items: deque[Track] = deque()



    # =====================================================
    # Добавление
    # =====================================================


    def add(
        self,
        track: Track
    ) -> None:
        """
        Добавить один трек.
        """

        self._items.append(
            track
        )



    def add_many(
        self,
        tracks: list[Track]
    ) -> None:
        """
        Добавить несколько треков.
        """

        self._items.extend(
            tracks
        )



    # =====================================================
    # Получение
    # =====================================================


    def get_next(
        self
    ) -> Optional[Track]:
        """
        Забрать следующий трек из очереди.
        """

        if self.empty():

            return None


        return self._items.popleft()



    def peek(
        self
    ) -> Optional[Track]:
        """
        Посмотреть следующий трек
        без удаления.
        """

        if self.empty():

            return None


        return self._items[0]



    # =====================================================
    # Информация
    # =====================================================


    def preview(
        self,
        limit: int = 5
    ) -> list[Track]:
        """
        Вернуть первые N треков.
        """

        return list(
            self._items
        )[:limit]



    def all(
        self
    ) -> list[Track]:
        """
        Вернуть копию всей очереди.
        """

        return list(
            self._items
        )



    def size(
        self
    ) -> int:
        """
        Количество элементов.
        """

        return len(
            self._items
        )



    def empty(
        self
    ) -> bool:
        """
        Проверка пустой очереди.
        """

        return not bool(
            self._items
        )



    # =====================================================
    # Очистка
    # =====================================================


    def clear(
        self
    ) -> None:
        """
        Полностью очистить очередь.
        """

        self._items.clear()
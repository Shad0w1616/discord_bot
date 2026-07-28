from __future__ import annotations

from collections import deque
from typing import Optional

from music.models import (
    Track,
    Playlist,
    QueueItem
)

from music.exceptions import (
    QueueEmptyError
)


class MusicQueue:
    """
    Менеджер очереди треков.

    Не знает ничего о:
    - Discord
    - FFmpeg
    - YouTube

    Отвечает только за порядок треков.
    """


    def __init__(self):

        self._queue: deque[QueueItem] = deque()

        self.current: Optional[Track] = None

        self.loop: bool = False


    # =====================================================
    # Добавление треков
    # =====================================================

    def add(
        self,
        track: Track
    ) -> QueueItem:
        """
        Добавляет один трек в очередь.
        """


        item = QueueItem(

            track=track,

            requester=track.requester,

            position=len(self._queue) + 1

        )


        self._queue.append(
            item
        )


        self._update_positions()


        return item



    def add_playlist(
        self,
        playlist: Playlist
    ) -> int:
        """
        Добавляет весь плейлист.

        Возвращает количество
        добавленных треков.
        """


        count = 0


        for track in playlist:

            self.add(
                track
            )

            count += 1


        return count



    # =====================================================
    # Получение следующего трека
    # =====================================================

    def next(self) -> Track:
        """
        Забирает следующий трек
        из очереди.
        """


        if not self._queue:

            raise QueueEmptyError(
                "Очередь пуста."
            )


        item = self._queue.popleft()


        self.current = item.track


        self._update_positions()


        return item.track



    def peek(
        self,
        amount: int = 5
    ) -> list[Track]:
        """
        Возвращает первые N треков
        без удаления.
        """


        items = list(
            self._queue
        )


        return [

            item.track

            for item in items[:amount]

        ]



    # =====================================================
    # Управление очередью
    # =====================================================

    def clear(self):
        """
        Полностью очищает очередь.
        """


        self._queue.clear()


        self._update_positions()



    def remove(
        self,
        index: int
    ) -> Track:
        """
        Удаляет трек по номеру.

        Индекс начинается с 1.
        """


        if index < 1:

            raise IndexError(
                "Индекс должен начинаться с 1."
            )


        if index > len(self._queue):

            raise IndexError(
                "Такого трека нет."
            )


        items = list(
            self._queue
        )


        removed = items.pop(
            index - 1
        )


        self._queue = deque(
            items
        )


        self._update_positions()


        return removed.track



    def shuffle(self):
        """
        Перемешивает очередь.
        """


        import random


        items = list(
            self._queue
        )


        random.shuffle(
            items
        )


        self._queue = deque(
            items
        )


        self._update_positions()



    # =====================================================
    # Loop
    # =====================================================

    def enable_loop(self):

        self.loop = True



    def disable_loop(self):

        self.loop = False



    def toggle_loop(self) -> bool:
        """
        Включает/выключает повтор.

        Возвращает новое состояние.
        """


        self.loop = not self.loop


        return self.loop



    def repeat_current(
        self
    ):
        """
        Добавляет текущий трек
        обратно в начало очереди.
        """


        if self.current:

            self._queue.appendleft(

                QueueItem(

                    track=self.current,

                    requester=self.current.requester

                )

            )


            self._update_positions()



    # =====================================================
    # Информация
    # =====================================================

    def get_all(
        self
    ) -> list[Track]:
        """
        Возвращает всю очередь.
        """


        return [

            item.track

            for item in self._queue

        ]



    def is_empty(
        self
    ) -> bool:
        """
        Проверка пустоты очереди.
        """


        return len(self._queue) == 0



    def size(
        self
    ) -> int:

        return len(
            self._queue
        )



    # =====================================================
    # Внутренние методы
    # =====================================================

    def _update_positions(
        self
    ):
        """
        Обновляет номера треков.
        """


        for index, item in enumerate(

            self._queue,

            start=1

        ):

            item.position = index



    def __len__(
        self
    ) -> int:

        return len(
            self._queue
        )



    def __bool__(
        self
    ) -> bool:

        return not self.is_empty()
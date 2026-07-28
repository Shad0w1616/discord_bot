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

        self.on_track_start = None

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
    # =====================================================
    # Pause / Resume
    # =====================================================


    def pause(
        self
    ) -> bool:
        """
        Ставит текущий трек на паузу.

        Возвращает:
        True если пауза установлена.
        """


        if not self.voice_client:

            return False


        if not self.voice_client.is_playing():

            return False


        self.voice_client.pause()


        self.paused = True


        logger.info(

            f"[{self.guild_id}] "
            "Воспроизведение поставлено на паузу."

        )


        return True



    def resume(
        self
    ) -> bool:
        """
        Продолжает воспроизведение.
        """


        if not self.voice_client:

            return False


        if not self.voice_client.is_paused():

            return False


        self.voice_client.resume()


        self.paused = False


        logger.info(

            f"[{self.guild_id}] "
            "Воспроизведение продолжено."

        )


        return True



    def toggle_pause(
        self
    ) -> bool:
        """
        Переключатель паузы.

        Используется командой:

        /sambovanie

        Возвращает новое состояние:

        True  - стоит на паузе
        False - играет
        """


        if self.paused:

            self.resume()

        else:

            self.pause()


        return self.paused



    # =====================================================
    # Skip
    # =====================================================


    async def skip(
        self
    ) -> bool:
        """
        Пропускает текущий трек.

        Следующий трек запускается
        автоматически через callback.
        """


        if not self.voice_client:

            return False



        if not self.voice_client.is_playing():

            return False



        logger.info(

            f"[{self.guild_id}] "
            "Трек пропущен."

        )


        self.voice_client.stop()


        return True



    # =====================================================
    # Stop
    # =====================================================


    async def stop(
        self
    ):
        """
        Полная остановка музыки.
        """


        if self.voice_client:

            if self.voice_client.is_playing():

                self.voice_client.stop()



        self.queue.clear()


        self.current = None


        self.paused = False


        logger.info(

            f"[{self.guild_id}] "
            "Воспроизведение остановлено."

        )



    # =====================================================
    # Volume
    # =====================================================


    def set_volume(
        self,
        volume: float
    ) -> float:
        """
        Устанавливает громкость.

        Значение:
        0.0 - 2.0
        """


        if volume < 0:

            volume = 0


        if volume > 2:

            volume = 2



        self.volume = volume



        if (

            self.voice_client

            and self.voice_client.source

        ):

            if isinstance(

                self.voice_client.source,

                discord.PCMVolumeTransformer

            ):

                self.voice_client.source.volume = volume



        return self.volume



    # =====================================================
    # Queue control
    # =====================================================


    def clear_queue(
        self
    ):
        """
        Очистка очереди.
        """


        self.queue.clear()


        logger.info(

            f"[{self.guild_id}] "
            "Очередь очищена."

        )



    def get_queue_preview(
        self,
        amount: int = 5
    ) -> list[Track]:
        """
        Получение первых N треков.
        """


        return self.queue.peek(
            amount
        )



    # =====================================================
    # Auto disconnect
    # =====================================================


    def start_disconnect_timer(
        self
    ):
        """
        Запускает таймер выхода
        из голосового канала.

        Если через 30 секунд
        нет новых треков —
        бот выходит.
        """


        if self.disconnect_task:

            self.disconnect_task.cancel()



        self.disconnect_task = asyncio.create_task(

            self._disconnect_after_timeout()

        )



    async def cancel_disconnect_timer(
        self
    ):
        """
        Отмена таймера выхода.
        """


        if self.disconnect_task:

            self.disconnect_task.cancel()


            self.disconnect_task = None



    async def _disconnect_after_timeout(
        self
    ):
        """
        Ожидание и выход.
        """


        try:

            await asyncio.sleep(

                settings.AUTO_DISCONNECT_TIMEOUT

            )


            if (

                not self.is_playing()

                and self.queue.is_empty()

            ):

                await self.disconnect()



        except asyncio.CancelledError:

            pass



    async def disconnect(
        self
    ):
        """
        Отключение от голосового канала.
        """


        if self.voice_client:

            await self.voice_client.disconnect()


            self.voice_client = None



        self.current = None


        self.queue.clear()



        logger.info(

            f"[{self.guild_id}] "
            "Отключился от голосового канала."

        )



    # =====================================================
    # Information
    # =====================================================


    def status(
        self
    ) -> dict:
        """
        Текущее состояние плеера.
        """


        return {

            "guild_id":
                self.guild_id,

            "playing":
                self.is_playing(),

            "paused":
                self.paused,

            "current":
                (
                    self.current.title
                    if self.current
                    else None
                ),

            "queue_size":
                self.queue.size()

        }
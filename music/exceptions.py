class MusicError(Exception):
    """
    Базовое исключение музыкального модуля.
    """


class QueueEmptyError(MusicError):
    """
    Очередь пуста.
    """


class TrackNotFoundError(MusicError):
    """
    Трек не найден.
    """


class InvalidYoutubeUrlError(MusicError):
    """
    Некорректная ссылка YouTube.
    """


class YoutubeSearchError(MusicError):
    """
    Ошибка поиска на YouTube.
    """


class AudioStreamError(MusicError):
    """
    Не удалось получить аудиопоток.
    """


class VoiceConnectionError(MusicError):
    """
    Ошибка подключения к голосовому каналу.
    """
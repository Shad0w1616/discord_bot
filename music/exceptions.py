class MusicException(Exception):
    """
    Базовое исключение музыкальной системы.
    """

    pass





class VoiceConnectionError(
    MusicException
):
    """
    Ошибка подключения к голосовому каналу.
    """

    pass





class TrackNotFoundError(
    MusicException
):
    """
    Трек не найден или недоступен.
    """

    pass





class PlaybackError(
    MusicException
):
    """
    Ошибка воспроизведения.
    """

    pass
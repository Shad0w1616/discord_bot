# import asyncio
# import os
# import re

# import discord
# from discord import app_commands
# from discord.ext import commands
# from dotenv import load_dotenv
# import yt_dlp


# # ============================================================
# # Загрузка переменных окружения
# # ============================================================

# load_dotenv()

# TOKEN = os.getenv("DISCORD_TOKEN")

# if not TOKEN:
#     raise RuntimeError(
#         "DISCORD_TOKEN не найден в файле .env"
#     )


# # ============================================================
# # Настройка Discord Intents
# # ============================================================

# intents = discord.Intents.default()
# intents.voice_states = True


# # ============================================================
# # Создание бота
# # ============================================================

# bot = commands.Bot(
#     command_prefix="!",
#     intents=intents
# )


# # ============================================================
# # Настройки yt-dlp
# # ============================================================

# YTDLP_OPTIONS = {
#     "format": "bestaudio/best",
#     "noplaylist": True,
#     "skip_download": True,
#     "quiet": True,
#     "no_warnings": True,
# }


# # ============================================================
# # Настройки FFmpeg
# # ============================================================

# FFMPEG_OPTIONS = {
#     "before_options": (
#         "-reconnect 1 "
#         "-reconnect_streamed 1 "
#         "-reconnect_delay_max 5"
#     ),
#     "options": "-vn",
# }


# # ============================================================
# # Путь к FFmpeg
# # ============================================================

# FFMPEG_PATH = r"C:\vsyach\ffmpeg-2026-07-27-git-a757b708ae-essentials_build\bin\ffmpeg.exe"


# # ============================================================
# # Проверка YouTube-ссылки
# # ============================================================

# YOUTUBE_URL_PATTERN = re.compile(
#     r"^(https?://)?(www\.)?"
#     r"(youtube\.com|youtu\.be)/.+$"
# )


# def is_youtube_url(query: str) -> bool:
#     return bool(
#         YOUTUBE_URL_PATTERN.match(query)
#     )


# # ============================================================
# # Получение информации о видео
# # ============================================================

# def get_video_info(query: str) -> dict:

#     if not is_youtube_url(query):
#         query = f"ytsearch1:{query}"

#     with yt_dlp.YoutubeDL(
#         YTDLP_OPTIONS
#     ) as ydl:

#         info = ydl.extract_info(
#             query,
#             download=False
#         )

#     if "entries" in info:

#         entries = info["entries"]

#         if not entries:
#             raise RuntimeError(
#                 "По вашему запросу ничего не найдено."
#             )

#         info = entries[0]

#     return info


# async def get_audio_info(query: str) -> dict:

#     loop = asyncio.get_running_loop()

#     return await loop.run_in_executor(
#         None,
#         get_video_info,
#         query
#     )


# # ============================================================
# # Событие запуска бота
# # ============================================================

# @bot.event
# async def on_ready():

#     try:

#         synced_commands = await bot.tree.sync()

#         print(
#             f"Бот успешно запущен: {bot.user}"
#         )

#         print(
#             f"Синхронизировано slash-команд: "
#             f"{len(synced_commands)}"
#         )

#     except Exception as error:

#         print(
#             f"Ошибка синхронизации команд: {error}"
#         )


# # ============================================================
# # Команда /notorious
# # ============================================================

# @bot.tree.command(
#     name="notorious",
#     description="Проиграть музыку из YouTube"
# )
# @app_commands.describe(
#     query="YouTube-ссылка или поисковый запрос"
# )
# async def notorious(
#     interaction: discord.Interaction,
#     query: str
# ):

#     if interaction.guild is None:

#         await interaction.response.send_message(
#             "❌ Эта команда должна использоваться "
#             "на Discord-сервере.",
#             ephemeral=True
#         )

#         return


#     member = interaction.user


#     if member.voice is None:

#         await interaction.response.send_message(
#             "❌ Сначала зайди в голосовой канал.",
#             ephemeral=True
#         )

#         return


#     voice_channel = member.voice.channel


#     await interaction.response.defer()


#     try:

#         info = await get_audio_info(query)

#         title = info.get(
#             "title",
#             "Неизвестный трек"
#         )

#         audio_url = info["url"]

#         voice_client = (
#             interaction.guild.voice_client
#         )


#         if voice_client is None:

#             voice_client = (
#                 await voice_channel.connect()
#             )


#         elif voice_client.channel != voice_channel:

#             await voice_client.move_to(
#                 voice_channel
#             )


#         if voice_client.is_playing():

#             voice_client.stop()


#         audio_source = (
#             discord.FFmpegPCMAudio(
#                 audio_url,
#                 executable=FFMPEG_PATH,
#                 **FFMPEG_OPTIONS
#             )
#         )


#         voice_client.play(
#             audio_source,

#             after=lambda error: (
#                 print(
#                     f"Ошибка воспроизведения: {error}"
#                 )
#                 if error
#                 else None
#             )
#         )


#         await interaction.followup.send(
#             f"▶️ Сейчас играет: **{title}**"
#         )


#     except Exception as error:

#         print(
#             f"Ошибка воспроизведения: {error}"
#         )

#         await interaction.followup.send(
#             "❌ Не удалось проиграть трек:\n"
#             f"`{error}`"
#         )


# # ============================================================
# # Команда /sambovanie
# # ============================================================

# @bot.tree.command(
#     name="sambovanie",
#     description="Поставить текущий трек на паузу"
# )
# async def sambovanie(
#     interaction: discord.Interaction
# ):

#     if interaction.guild is None:

#         await interaction.response.send_message(
#             "❌ Эта команда должна использоваться "
#             "на Discord-сервере.",
#             ephemeral=True
#         )

#         return


#     voice_client = (
#         interaction.guild.voice_client
#     )


#     if voice_client is None:

#         await interaction.response.send_message(
#             "❌ Бот не подключён к голосовому каналу.",
#             ephemeral=True
#         )

#         return


#     if not voice_client.is_playing():

#         await interaction.response.send_message(
#             "❌ Сейчас ничего не играет.",
#             ephemeral=True
#         )

#         return


#     voice_client.pause()


#     await interaction.response.send_message(
#         "⏸️ Трек поставлен на паузу."
#     )


# # ============================================================
# # Запуск бота
# # ============================================================

# bot.run(TOKEN)
import asyncio
import os
import re

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp


# ============================================================
# Загрузка переменных окружения
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN не найден в файле .env"
    )


# ============================================================
# Discord Intents
# ============================================================

intents = discord.Intents.default()
intents.voice_states = True


# ============================================================
# Создание бота
# ============================================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# Настройки yt-dlp
# ============================================================

YTDLP_OPTIONS = {
    "format": "bestaudio/best",

    # Теперь плейлисты разрешены
    "noplaylist": False,

    "skip_download": True,

    "quiet": True,

    "no_warnings": True,
}


# ============================================================
# Настройки FFmpeg
# ============================================================

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),

    "options": "-vn",
}


# ============================================================
# Путь к FFmpeg
# ============================================================

FFMPEG_PATH = (
    r"C:\vsyach\ffmpeg-2026-07-27-git-a757b708ae-essentials_build\bin\ffmpeg.exe"
)


# ============================================================
# Регулярные выражения для YouTube
# ============================================================

YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com|youtu\.be)/.+$"
)


YOUTUBE_PLAYLIST_PATTERN = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com|www\.youtube-nocookie\.com)"
    r"/(playlist\?list=|watch\?.*list=).+$"
)


# ============================================================
# Проверка YouTube-ссылки
# ============================================================

def is_youtube_url(query: str) -> bool:

    return bool(
        YOUTUBE_URL_PATTERN.match(query)
    )


# ============================================================
# Проверка YouTube-плейлиста
# ============================================================

def is_youtube_playlist(query: str) -> bool:

    return bool(
        YOUTUBE_PLAYLIST_PATTERN.match(query)
    )


# ============================================================
# Получение информации о треке или плейлисте
# ============================================================

def get_video_info(query: str) -> dict:

    # Если пользователь ввёл обычный текст,
    # ищем первый результат на YouTube
    if not is_youtube_url(query):

        query = (
            f"ytsearch1:{query}"
        )


    with yt_dlp.YoutubeDL(
        YTDLP_OPTIONS
    ) as ydl:

        info = ydl.extract_info(
            query,
            download=False
        )


    # Если это обычный поисковый запрос,
    # берём первый результат
    if "entries" in info:

        entries = info["entries"]


        # Для плейлиста entries содержит
        # все видео.
        #
        # Для ytsearch1 entries содержит
        # один результат.


        if not entries:

            raise RuntimeError(
                "По вашему запросу ничего не найдено."
            )


        # Если это плейлист,
        # возвращаем всю информацию
        if info.get("_type") == "playlist":

            return info


        # Если это результат поиска,
        # возвращаем первый трек
        return entries[0]


    return info


async def get_audio_info(
    query: str
) -> dict:

    loop = asyncio.get_running_loop()


    return await loop.run_in_executor(
        None,
        get_video_info,
        query
    )


# ============================================================
# Очередь треков
# ============================================================

music_queues = {}


# ============================================================
# Задачи автоматического выхода
# ============================================================

leave_tasks = {}


# ============================================================
# Текущий трек
# ============================================================

current_tracks = {}


# ============================================================
# Вывод следующих пяти треков
# ============================================================

async def send_queue(
    guild: discord.Guild,
    channel: discord.abc.Messageable
):

    guild_id = guild.id


    queue = music_queues.get(
        guild_id,
        []
    )


    if not queue:

        await channel.send(
            "📭 Очередь пуста."
        )

        return


    next_tracks = queue[:5]


    message = (
        "📋 **Следующие треки в очереди:**\n\n"
    )


    for index, track in enumerate(
        next_tracks,
        start=1
    ):

        message += (
            f"**{index}.** "
            f"{track['title']}\n"
        )


    await channel.send(
        message
    )


# ============================================================
# Запуск следующего трека
# ============================================================

async def play_next(
    guild: discord.Guild,
    text_channel: discord.abc.Messageable
):

    guild_id = guild.id


    voice_client = (
        guild.voice_client
    )


    if voice_client is None:

        return


    queue = music_queues.get(
        guild_id,
        []
    )


    # Если очередь закончилась
    if not queue:

        current_tracks.pop(
            guild_id,
            None
        )


        await schedule_leave(
            guild
        )


        return


    # Берём первый трек
    track = queue.pop(0)


    current_tracks[
        guild_id
    ] = track


    # Создаём источник аудио
    audio_source = (
        discord.FFmpegPCMAudio(
            track["url"],

            executable=FFMPEG_PATH,

            **FFMPEG_OPTIONS
        )
    )


    # Callback после завершения трека
    def after_playing(error):

        if error:

            print(
                f"Ошибка воспроизведения: {error}"
            )


        asyncio.run_coroutine_threadsafe(
            play_next(
                guild,
                text_channel
            ),

            bot.loop
        )


    # Запускаем воспроизведение
    voice_client.play(
        audio_source,

        after=after_playing
    )


    # Отменяем таймер выхода
    cancel_leave_task(
        guild_id
    )


    # Сообщаем о текущем треке
    await text_channel.send(
        "▶️ **Сейчас играет:**\n"
        f"**{track['title']}**"
    )


    # Показываем очередь
    await send_queue(
        guild,
        text_channel
    )


# ============================================================
# Автоматический выход через 30 секунд
# ============================================================

async def leave_after_30_seconds(
    guild: discord.Guild
):

    guild_id = guild.id


    try:

        await asyncio.sleep(
            30
        )


        queue = music_queues.get(
            guild_id,
            []
        )


        voice_client = (
            guild.voice_client
        )


        if (
            not queue
            and voice_client is not None
            and not voice_client.is_playing()
            and not voice_client.is_paused()
        ):

            await voice_client.disconnect()


            current_tracks.pop(
                guild_id,
                None
            )


            music_queues.pop(
                guild_id,
                None
            )


    except asyncio.CancelledError:

        pass


    finally:

        leave_tasks.pop(
            guild_id,
            None
        )


async def schedule_leave(
    guild: discord.Guild
):

    guild_id = guild.id


    if guild_id in leave_tasks:

        return


    leave_tasks[
        guild_id
    ] = asyncio.create_task(
        leave_after_30_seconds(
            guild
        )
    )


def cancel_leave_task(
    guild_id: int
):

    task = leave_tasks.get(
        guild_id
    )


    if task:

        task.cancel()


        leave_tasks.pop(
            guild_id,
            None
        )


# ============================================================
# Событие запуска бота
# ============================================================

@bot.event
async def on_ready():

    try:

        synced_commands = (
            await bot.tree.sync()
        )


        print(
            f"Бот успешно запущен: {bot.user}"
        )


        print(
            "Синхронизировано slash-команд: "
            f"{len(synced_commands)}"
        )


    except Exception as error:

        print(
            f"Ошибка синхронизации команд: {error}"
        )


# ============================================================
# Команда /notorious
# ============================================================

@bot.tree.command(
    name="notorious",
    description="Добавить музыку из YouTube"
)
@app_commands.describe(
    query=(
        "YouTube-ссылка, ссылка на плейлист "
        "или поисковый запрос"
    )
)
async def notorious(
    interaction: discord.Interaction,
    query: str
):

    # Проверяем сервер
    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ Эта команда должна использоваться "
            "на Discord-сервере.",

            ephemeral=True
        )

        return


    # Проверяем голосовой канал
    if interaction.user.voice is None:

        await interaction.response.send_message(
            "❌ Сначала зайди в голосовой канал.",

            ephemeral=True
        )

        return


    voice_channel = (
        interaction.user.voice.channel
    )


    await interaction.response.defer()


    try:

        # Получаем информацию
        # о треке или плейлисте
        info = await get_audio_info(
            query
        )


        guild_id = (
            interaction.guild.id
        )


        # Инициализируем очередь
        if guild_id not in music_queues:

            music_queues[
                guild_id
            ] = []


        # Подключаем бота
        voice_client = (
            interaction.guild.voice_client
        )


        if voice_client is None:

            voice_client = (
                await voice_channel.connect()
            )


        elif voice_client.channel != voice_channel:

            await voice_client.move_to(
                voice_channel
            )


        # Отменяем таймер выхода
        cancel_leave_task(
            guild_id
        )


        # ====================================================
        # Если это плейлист
        # ====================================================

        if info.get(
            "_type"
        ) == "playlist":

            entries = info.get(
                "entries",
                []
            )


            added_tracks = []


            for entry in entries:

                # Некоторые элементы
                # плейлиста могут быть недоступны
                if not entry:

                    continue


                title = entry.get(
                    "title"
                )


                video_url = entry.get(
                    "webpage_url"
                )


                # Иногда webpage_url отсутствует.
                # Тогда формируем URL
                # из video_id
                if not video_url:

                    video_id = entry.get(
                        "id"
                    )


                    if video_id:

                        video_url = (
                            "https://www.youtube.com/watch?v="
                            f"{video_id}"
                        )


                if not title or not video_url:

                    continue


                track = {

                    "title": title,

                    "url": video_url,

                }


                music_queues[
                    guild_id
                ].append(
                    track
                )


                added_tracks.append(
                    track
                )


            if not added_tracks:

                await interaction.followup.send(
                    "❌ В плейлисте не найдено "
                    "доступных треков."
                )

                return


            # Если ничего не играет,
            # запускаем первый трек
            if not voice_client.is_playing():

                await play_next(
                    interaction.guild,

                    interaction.channel
                )


                # Убираем первый трек
                # из текста ответа,
                # потому что он уже запущен
                started_title = (
                    added_tracks[0]["title"]
                )


                await interaction.followup.send(
                    "🎵 Плейлист добавлен.\n"
                    f"Добавлено треков: "
                    f"**{len(added_tracks)}**\n"
                    f"▶️ Начинает играть: "
                    f"**{started_title}**"
                )


            else:

                await interaction.followup.send(
                    "🎵 Плейлист добавлен в очередь.\n"
                    f"Добавлено треков: "
                    f"**{len(added_tracks)}**"
                )


        # ====================================================
        # Если это одиночный трек
        # ====================================================

        else:

            title = info.get(
                "title",
                "Неизвестный трек"
            )


            audio_url = info.get(
                "webpage_url"
            )


            # Если webpage_url отсутствует,
            # используем исходный запрос
            if not audio_url:

                audio_url = query


            track = {

                "title": title,

                "url": audio_url,

            }


            # Добавляем в очередь
            music_queues[
                guild_id
            ].append(
                track
            )


            # Если ничего не играет,
            # запускаем первый трек
            if not voice_client.is_playing():

                await play_next(
                    interaction.guild,

                    interaction.channel
                )


            else:

                position = len(
                    music_queues[
                        guild_id
                    ]
                )


                await interaction.followup.send(
                    "➕ Трек добавлен в очередь:\n"
                    f"**{title}**\n"
                    f"Позиция: **{position}**"
                )


    except Exception as error:

        print(
            f"Ошибка добавления трека: {error}"
        )


        await interaction.followup.send(
            "❌ Не удалось добавить трек:\n"
            f"`{error}`"
        )


# ============================================================
# Команда /sambovanie
# ============================================================

@bot.tree.command(
    name="sambovanie",
    description=(
        "Поставить трек на паузу "
        "или продолжить"
    )
)
async def sambovanie(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ Эта команда должна использоваться "
            "на Discord-сервере.",

            ephemeral=True
        )

        return


    voice_client = (
        interaction.guild.voice_client
    )


    if voice_client is None:

        await interaction.response.send_message(
            "❌ Бот не подключён "
            "к голосовому каналу.",

            ephemeral=True
        )

        return


    # Пауза
    if voice_client.is_playing():

        voice_client.pause()


        await interaction.response.send_message(
            "⏸️ Трек поставлен на паузу."
        )


    # Продолжение
    elif voice_client.is_paused():

        voice_client.resume()


        await interaction.response.send_message(
            "▶️ Воспроизведение продолжено."
        )


    else:

        await interaction.response.send_message(
            "❌ Сейчас ничего не играет.",

            ephemeral=True
        )


# ============================================================
# Команда /next
# ============================================================

@bot.tree.command(
    name="next",
    description="Пропустить текущий трек"
)
async def next_track(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ Эта команда должна использоваться "
            "на Discord-сервере.",

            ephemeral=True
        )

        return


    voice_client = (
        interaction.guild.voice_client
    )


    if voice_client is None:

        await interaction.response.send_message(
            "❌ Бот не подключён "
            "к голосовому каналу.",

            ephemeral=True
        )

        return


    if (
        not voice_client.is_playing()
        and not voice_client.is_paused()
    ):

        await interaction.response.send_message(
            "❌ Сейчас ничего не играет.",

            ephemeral=True
        )

        return


    # Останавливаем текущий трек.
    # Callback автоматически
    # запустит следующий.
    voice_client.stop()


    await interaction.response.send_message(
        "⏭️ Текущий трек пропущен."
    )


# ============================================================
# Запуск бота
# ============================================================

bot.run(TOKEN)

import asyncio

import discord

from discord.ext import commands

from config import settings
from utils.logger import setup_logger
from services.voice import VoiceManager

# Временные импорты.
# Позже здесь будут setup-функции из commands/
from commands.music import setup_music_commands
from commands.admin import setup_admin_commands

logger = setup_logger()

EXTENSIONS = [

    "commands.music",

    "commands.admin"

]
def create_bot() -> commands.Bot:
    """
    Создает и настраивает экземпляр Discord-бота.
    """

    intents = discord.Intents.default()
    intents.voice_states = True
    intents.guilds = True

    bot = commands.Bot(
        command_prefix=settings.COMMAND_PREFIX,
        intents=intents
    )

    return bot




bot = create_bot()

bot.voice_manager = VoiceManager()

async def load_extensions():

    for extension in EXTENSIONS:

        try:

            await bot.load_extension(
                extension
            )


            logger.info(

                f"Загружено расширение: {extension}"

            )


        except Exception:

            logger.exception(

                f"Ошибка загрузки {extension}"

            )

@bot.event
async def on_ready():

    logger.info(
        "Авторизация успешна."
    )

    logger.info(
        f"Бот: {bot.user}"
    )

    logger.info(
        f"ID: {bot.user.id}"
    )

    try:

        synced = await bot.tree.sync()

        logger.info(
            f"Slash-команд синхронизировано: {len(synced)}"
        )

    except Exception:

        logger.exception(
            "Не удалось синхронизировать команды."
        )
async def main():

    logger.info(
        "Запуск бота..."
    )


    await load_extensions()


    await bot.start(

        settings.DISCORD_TOKEN

    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
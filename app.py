from __future__ import annotations

import asyncio
import signal
import sys
import discord
from discord.ext import commands

from settings import settings
from services.voice import VoiceManager

from utils.logger import logger
def check_opus():

    if discord.opus.is_loaded():
        return


    discord.opus.load_opus(
        r"C:\vsyach\opus\libopus-0.x64.dll"
    )


    if not discord.opus.is_loaded():

        raise RuntimeError(
            "Opus loading failed"
        )

class NotoriousBot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.default()

        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix=settings.COMMAND_PREFIX,
            intents=intents
        )

        self.voice_manager = VoiceManager(
            self
        )

        self._closing = False


    async def setup_hook(self):

        await self.load_extension(
            "cogs.music"
        )

        await self.load_extension(
            "cogs.admin"
        )

        synced = await self.tree.sync()

        logger.info(
            f"Loaded commands: {[cmd.name for cmd in synced]}"
        )
    

    async def on_ready(self):

        logger.info(
            f"Bot online: {self.user}"
        )


    async def close(self):

        if self._closing:
            return

        self._closing = True

        logger.info(
            "Bot shutdown started"
        )

        await self.voice_manager.shutdown()

        await super().close()



bot = NotoriousBot()



async def shutdown():

    await bot.close()



def register_signals():

    # Windows не поддерживает asyncio.add_signal_handler()
    if sys.platform == "win32":

        return


    loop = asyncio.get_running_loop()


    for sig in (
        signal.SIGINT,
        signal.SIGTERM
    ):

        loop.add_signal_handler(

            sig,

            lambda: asyncio.create_task(
                shutdown()
            )

        )
async def main():

    if not settings.DISCORD_TOKEN:

        raise RuntimeError(
            "DISCORD_TOKEN is missing"
        )


    check_opus()


    register_signals()


    async with bot:

        await bot.start(
            settings.DISCORD_TOKEN
        )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
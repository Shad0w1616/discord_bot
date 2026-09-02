# from __future__ import annotations

# import asyncio
# import signal
# import sys
# import discord
# from discord.ext import commands

# from settings import settings
# from services.voice import VoiceManager

# from utils.logger import logger

# def check_opus():

#     if discord.opus.is_loaded():
#         return


#     # discord.opus.load_opus(
#     #     r"C:\vsyach\opus\libopus-0.x64.dll"
#     # )
#     discord.opus.load_opus(
#         "libopus.so.0"
#     )


#     if not discord.opus.is_loaded():

#         raise RuntimeError(
#             "Opus loading failed"
#         )

# class NotoriousBot(commands.Bot):

#     def __init__(self):

#         intents = discord.Intents.default()

#         intents.message_content = True
#         intents.voice_states = True

#         super().__init__(
#             command_prefix=settings.COMMAND_PREFIX,
#             intents=intents
#         )

#         self.voice_manager = VoiceManager(
#             self
#         )

#         self._closing = False


#     async def setup_hook(self):

#         await self.load_extension(
#             "cogs.music"
#         )

#         await self.load_extension(
#             "cogs.admin"
#         )

#         synced = await self.tree.sync()

#         logger.info(
#             f"Loaded commands: {[cmd.name for cmd in synced]}"
#         )
    

#     async def on_ready(self):

#         logger.info(
#             f"Bot online: {self.user}"
#         )


#     async def close(self):

#         if self._closing:
#             return

#         self._closing = True

#         logger.info(
#             "Bot shutdown started"
#         )

#         await self.voice_manager.shutdown()

#         await super().close()



# bot = NotoriousBot()



# async def shutdown():

#     await bot.close()



# def register_signals():

#     # Windows не поддерживает asyncio.add_signal_handler()
#     if sys.platform == "win32":

#         return


#     loop = asyncio.get_running_loop()


#     for sig in (
#         signal.SIGINT,
#         signal.SIGTERM
#     ):

#         loop.add_signal_handler(

#             sig,

#             lambda: asyncio.create_task(
#                 shutdown()
#             )

#         )
# async def main():

#     if not settings.DISCORD_TOKEN:

#         raise RuntimeError(
#             "DISCORD_TOKEN is missing"
#         )


#     check_opus()


#     register_signals()


#     async with bot:

#         await bot.start(
#             settings.DISCORD_TOKEN
#         )


# if __name__ == "__main__":

#     asyncio.run(
#         main()
#     )
from __future__ import annotations

import asyncio
import signal
import sys
import discord
from discord.ext import commands
from aiohttp import web

from settings import settings
from services.voice import VoiceManager

from utils.logger import logger

def check_opus():

    if discord.opus.is_loaded():
        return


    discord.opus.load_opus(
        "libopus.so.0"
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

        self.voice_manager = VoiceManager(self)
        self._closing = False
        self.discord_ready = False

    async def setup_hook(self):
        await self.load_extension("cogs.music")
        await self.load_extension("cogs.admin")

        synced = await self.tree.sync()

        logger.info(
            f"Loaded commands: {[cmd.name for cmd in synced]}"
        )

    async def on_ready(self):
        self.discord_ready = True

        logger.info(
            f"Bot online: {self.user}"
        )

    async def close(self):
        if self._closing:
            return

        self._closing = True
        self.discord_ready = False

        logger.info(
            "Bot shutdown started"
        )

        await self.voice_manager.shutdown()
        await super().close()
# class NotoriousBot(commands.Bot):

#     def __init__(self):

#         intents = discord.Intents.default()

#         intents.message_content = True
#         intents.voice_states = True

#         super().__init__(
#             command_prefix=settings.COMMAND_PREFIX,
#             intents=intents
#         )

#         self.voice_manager = VoiceManager(
#             self
#         )

#         self._closing = False


#     async def setup_hook(self):

#         await self.load_extension(
#             "cogs.music"
#         )

#         await self.load_extension(
#             "cogs.admin"
#         )

#         synced = await self.tree.sync()

#         logger.info(
#             f"Loaded commands: {[cmd.name for cmd in synced]}"
#         )
    

#     async def on_ready(self):

#         logger.info(
#             f"Bot online: {self.user}"
#         )


#     async def close(self):

#         if self._closing:
#             return

#         self._closing = True

#         logger.info(
#             "Bot shutdown started"
#         )

#         await self.voice_manager.shutdown()

#         await super().close()



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
async def health(request):
    if bot.discord_ready and not bot.is_closed():
        return web.Response(
            status=200,
            text="OK"
        )

    return web.Response(
        status=503,
        text="Discord is not ready"
    )


async def start_health_server():
    app = web.Application()

    app.router.add_get(
        "/health",
        health
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "127.0.0.1",
        8080
    )

    await site.start()

    logger.info(
        "Healthcheck server started on 127.0.0.1:8080"
    )

    return runner
from aiohttp import web
import asyncio

async def health(request):
    return web.Response(text="OK")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
async def main():

    if not settings.DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing"
        )

    check_opus()

    register_signals()

    health_runner = await start_health_server()

    try:
        async with bot:
            await bot.start(
                settings.DISCORD_TOKEN
            )

    finally:
        await health_runner.cleanup()
# async def main():

#     if not settings.DISCORD_TOKEN:

#         raise RuntimeError(
#             "DISCORD_TOKEN is missing"
#         )


#     check_opus()


#     register_signals()


#     async with bot:

#         await bot.start(
#             settings.DISCORD_TOKEN
#         )


if __name__ == "__main__":

    asyncio.run(
        main()
    )

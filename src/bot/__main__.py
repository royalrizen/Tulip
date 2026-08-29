import asyncio
import logging

from .core import Bot, Config
from .web import start_web
from .utils import setup_discord_logger


def main():
    asyncio.run(run())

async def run():
    config = Config.load()
    start_web()
    bot = Bot(config)
    setup_discord_logger(bot)
    logging.getLogger("bot").info(
        "Discord logger initialized."
    )

    async with bot:
        await bot.start(config.token)


if __name__ == "__main__":
    main()
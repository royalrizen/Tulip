import asyncio
import logging

import discord
from discord.ext import commands

from .config import Config
from .loader import load_cogs
from .logging import setup_logging

from bot.database import Database, create_tables


logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=config.prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand(),
        )

        self.config = config

        self.db = Database(
            host=config.mysql_host,
            port=config.mysql_port,
            user=config.mysql_user,
            password=config.mysql_password,
            database=config.mysql_database,
        )

        self.database_keepalive_task = None

        setup_logging(self)

    async def setup_hook(self):
        await self.db.connect()

        await create_tables(self.db)

        self.database_keepalive_task = asyncio.create_task(
            self.database_keepalive()
        )

        await load_cogs(self)

        await self.tree.sync()

    async def database_keepalive(self):
        await self.wait_until_ready()

        while not self.is_closed():
            try:
                await self.db.fetchval(
                    "SELECT 1"
                )

                logger.debug(
                    "Database keep-alive successful."
                )

            except Exception:
                logger.exception(
                    "Database keep-alive failed."
                )

                try:
                    await self.db.connect()
                except Exception:
                    logger.exception(
                        "Failed to reconnect to database."
                    )

            await asyncio.sleep(300)

    async def close(self):
        if self.database_keepalive_task:
            self.database_keepalive_task.cancel()

            try:
                await self.database_keepalive_task
            except asyncio.CancelledError:
                pass

        await self.db.close()

        await super().close()

    async def on_ready(self):
        logger.info(
            "Logged in as %s (%s)",
            self.user,
            self.user.id,
        )

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

        setup_logging(self)

    async def setup_hook(self):
        await self.db.connect()
        await create_tables(self.db)

        await load_cogs(self)
        await self.tree.sync()

    async def close(self):
        await self.db.close()
        await super().close()

    async def on_ready(self):
        logger.info(
            "Logged in as %s (%s)",
            self.user,
            self.user.id,
        )
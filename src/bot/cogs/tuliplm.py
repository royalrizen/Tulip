import logging
import time
from pathlib import Path
import discord
from discord.ext import commands, tasks
from bot.database import get_model_config, set_model_message
from bot.llm import learn, load, save

logger = logging.getLogger(__name__)
MODEL_FILE = Path("model.bin")

class TulipLM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_save: dict[int, float] = {}
        self.initialized = False

        self.save_task.start()

    def cog_unload(self):
        self.save_task.cancel()

    async def initialize_model(self):
        for guild in self.bot.guilds:
            config = await get_model_config(
                self.bot.db,
                guild.id,
            )

            if config is None:
                continue

            channel_id = config["channel_id"]
            message_id = config["message_id"]

            channel = self.bot.get_channel(channel_id)

            if channel is None:
                logger.warning(
                    "LLM channel not found | Guild: %s | Channel: %s",
                    guild.id,
                    channel_id,
                )
                return

            if message_id is None:
                logger.info(
                    "No saved model found | Guild: %s",
                    guild.id,
                )
                return

            try:
                message = await channel.fetch_message(message_id)

                if not message.attachments:
                    logger.warning(
                        "Model message has no attachment | Guild: %s",
                        guild.id,
                    )
                    return

                attachment = message.attachments[0]
                data = await attachment.read()

                MODEL_FILE.write_bytes(data)

                load(str(MODEL_FILE))

                logger.info(
                    "Model loaded | Guild: %s | Message: %s",
                    guild.id,
                    message_id,
                )

            except (discord.HTTPException, OSError):
                logger.exception(
                    "Failed to load model | Guild: %s",
                    guild.id,
                )

            return

        logger.info("No LLM configuration found.")

    @commands.Cog.listener()
    async def on_ready(self):
        if self.initialized:
            return

        await self.initialize_model()
        self.initialized = True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.initialized:
            return

        if message.author.bot:
            return

        if message.guild is None:
            return

        config = await get_model_config(
            self.bot.db,
            message.guild.id,
        )

        if config is None:
            return

        text = message.content.strip()

        if not text:
            return

        learn(
            f"{message.author}: {text}"
        )

    @tasks.loop(seconds=60)
    async def save_task(self):
        if not self.initialized:
            return

        now = time.time()

        for guild in self.bot.guilds:
            config = await get_model_config(
                self.bot.db,
                guild.id,
            )

            if config is None:
                continue

            interval = config["save_interval"]
            channel_id = config["channel_id"]

            last_save = self.last_save.get(
                guild.id,
                now,
            )

            if now - last_save < interval:
                continue

            channel = self.bot.get_channel(channel_id)

            if channel is None:
                logger.warning(
                    "LLM channel not found | Guild: %s | Channel: %s",
                    guild.id,
                    channel_id,
                )
                continue

            try:
                save(str(MODEL_FILE))

                message = await channel.send(
                    file=discord.File(
                        str(MODEL_FILE),
                        filename="model.bin",
                    )
                )

                await set_model_message(
                    self.bot.db,
                    guild.id,
                    message.id,
                )

                self.last_save[guild.id] = now

                logger.info(
                    "Model saved | Guild: %s | Message: %s",
                    guild.id,
                    message.id,
                )

            except (discord.HTTPException, OSError):
                logger.exception(
                    "Failed to save model | Guild: %s",
                    guild.id,
                )

    @save_task.before_loop
    async def before_save_task(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(TulipLM(bot))

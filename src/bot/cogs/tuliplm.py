import logging
import time
import discord
from discord.ext import commands, tasks
from bot.database import get_model_config, set_model_message
from bot.llm import learn, save

logger = logging.getLogger(__name__)

class TulipLM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_save: dict[int, float] = {}

        self.save_task.start()

    def cog_unload(self):
        self.save_task.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
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
        now = time.time()

        configs = []

        for guild in self.bot.guilds:
            config = await get_model_config(
                self.bot.db,
                guild.id,
            )

            if config is not None:
                configs.append(
                    (guild.id, config)
                )

        for guild_id, config in configs:
            interval = config["save_interval"]
            channel_id = config["channel_id"]

            last_save = self.last_save.get(
                guild_id,
                now,
            )

            if now - last_save < interval:
                continue

            channel = self.bot.get_channel(channel_id)

            if channel is None:
                logger.warning(
                    "LLM channel not found | Guild: %s | Channel: %s",
                    guild_id,
                    channel_id,
                )
                continue

            save("model.bin")

            try:
                message = await channel.send(
                    file=discord.File(
                        "model.bin",
                        filename="model.bin",
                    )
                )

                await set_model_message(
                    self.bot.db,
                    guild_id,
                    message.id,
                )

                self.last_save[guild_id] = now

                logger.info(
                    "Model saved | Guild: %s | Channel: %s | Message: %s",
                    guild_id,
                    channel_id,
                    message.id,
                )

            except discord.HTTPException:
                logger.exception(
                    "Failed to upload model | Guild: %s",
                    guild_id,
                )

    @save_task.before_loop
    async def before_save_task(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(TulipLM(bot))

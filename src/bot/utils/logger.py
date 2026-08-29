import asyncio
import logging

import discord

from bot.database import get_logging_channel
from bot.utils import error, info, warning


class DiscordHandler(logging.Handler):
    def __init__(self, bot):
        super().__init__(logging.INFO)
        self.bot = bot
        self.loop = asyncio.get_running_loop()

    def emit(self, record: logging.LogRecord):
        if self.loop.is_closed():
            return

        try:
            asyncio.run_coroutine_threadsafe(
                self.send(record),
                self.loop,
            )
        except Exception:
            pass

    async def send(self, record: logging.LogRecord):
        if not self.bot.is_ready():
            return

        if not hasattr(self.bot, "db"):
            return

        for guild in tuple(self.bot.guilds):
            try:
                channel_id = await get_logging_channel(
                    self.bot.db,
                    guild.id,
                )

                if not channel_id:
                    continue

                channel = guild.get_channel(channel_id)

                if channel is None:
                    try:
                        channel = await self.bot.fetch_channel(
                            channel_id
                        )
                    except (
                        discord.NotFound,
                        discord.Forbidden,
                        discord.HTTPException,
                    ):
                        continue

                if not isinstance(
                    channel,
                    discord.TextChannel,
                ):
                    continue

                message = record.getMessage()

                if len(message) > 3800:
                    message = message[:3797] + "..."

                timestamp = f"<t:{int(record.created)}:f>"

                formatted_message = (
                    f"**{timestamp}** | "
                    f"`{record.levelname}` | "
                    f"`{record.name}`\n"
                    f"{message}"
                )

                if record.levelno >= logging.ERROR:
                    embed = error(formatted_message)

                elif record.levelno >= logging.WARNING:
                    embed = warning(formatted_message)

                else:
                    embed = info(formatted_message)

                await channel.send(
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none(),
                )

            except Exception:
                pass


def setup_discord_logger(bot):
    root = logging.getLogger()

    root.setLevel(logging.INFO)

    for handler in root.handlers:
        if isinstance(handler, DiscordHandler):
            return handler

    handler = DiscordHandler(bot)

    root.addHandler(handler)

    return handler
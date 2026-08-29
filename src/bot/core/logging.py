import logging
import sys

from bot.utils import DiscordHandler

def setup_logging(bot):
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    discord_handler = DiscordHandler(bot)
    discord_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    root.addHandler(console)
    root.addHandler(discord_handler)
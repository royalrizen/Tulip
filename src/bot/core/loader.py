from pathlib import Path
import logging

logger = logging.getLogger(__name__)


async def load_cogs(bot):
    cogs_path = Path(__file__).parent.parent / "cogs"

    for file in cogs_path.glob("*.py"):
        if file.name.startswith("_"):
            continue

        extension = f"bot.cogs.{file.stem}"

        await bot.load_extension(extension)
        logger.info("Loaded extension: %s", extension)
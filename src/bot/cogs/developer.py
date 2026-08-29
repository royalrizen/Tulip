import discord
from discord import app_commands
from discord.ext import commands

from bot.database import set_logging_channel
from bot.utils import error, is_bot_owner, success


class Developer(commands.Cog):
    dev = app_commands.Group(
        name="dev",
        description="Developer commands.",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @dev.command(
        name="logging",
        description="Set the server's logging channel.",
    )
    @app_commands.check(is_bot_owner)
    async def logging(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error(
                    "This command can only be used in a server."
                ),
                ephemeral=True,
            )
            return

        await set_logging_channel(
            self.bot.db,
            interaction.guild.id,
            channel.id,
        )

        await interaction.response.send_message(
            embed=success(
                f"Logging channel set to {channel.mention}."
            ),
            ephemeral=True,
        )

    @logging.error
    async def logging_error(
        self,
        interaction: discord.Interaction,
        exception: app_commands.AppCommandError,
    ):
        if isinstance(exception, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=error(
                    "You don't have permission to use this command."
                ),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Developer(bot))
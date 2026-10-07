import os
import time

import aiohttp
import discord
import psutil
from discord import app_commands
from discord.ext import commands

from bot.database import (
    set_logging_channel,
    set_model_config,
)
from bot.utils import error, is_bot_owner, success

FONTS = {
    1: "Bangers",
    2: "BioRhyme",
    3: "Cherry Bomb One",
    4: "Chicle",
    5: "Compagnon",
    6: "MuseoModerno",
    7: "Néo-Castel",
    8: "Pixelify Sans",
    9: "Ribes",
    10: "Sinistre",
    11: "Default",
    12: "Zilla Slab",
}

EFFECTS = {
    1: "Solid",
    2: "Gradient",
    3: "Neon",
    4: "Toon",
    5: "Pop",
    6: "Glow",
}

class Developer(commands.Cog):
    dev = app_commands.Group(
        name="dev",
        description="Developer commands.",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.start_time = getattr(
            self.bot,
            "start_time",
            time.monotonic(),
        )

    def get_cogs(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "cogs",
        )

        if not os.path.isdir(path):
            return []

        return sorted(
            file[:-3]
            for file in os.listdir(path)
            if file.endswith(".py")
            and file != "__init__.py"
        )

    async def cog_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        cogs = self.get_cogs()
        current = current.lower()

        return [
            app_commands.Choice(name=cog, value=cog)
            for cog in cogs
            if current in cog.lower()
        ][:25]

    @dev.command(
        name="load",
        description="Load a cog.",
    )
    @app_commands.check(is_bot_owner)
    @app_commands.autocomplete(cog=cog_autocomplete)
    async def load(
        self,
        interaction: discord.Interaction,
        cog: str,
    ):
        extension = f"bot.cogs.{cog}"

        try:
            await self.bot.load_extension(extension)
        except commands.ExtensionAlreadyLoaded:
            await interaction.response.send_message(
                embed=error(f"`{cog}` is already loaded."),
                ephemeral=True,
            )
            return
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                embed=error(f"Cog `{cog}` was not found."),
                ephemeral=True,
            )
            return
        except commands.ExtensionError as e:
            await interaction.response.send_message(
                embed=error(f"Failed to load `{cog}`:\n`{e}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success(f"Loaded `{cog}`."),
            ephemeral=True,
        )

    @dev.command(
        name="unload",
        description="Unload a cog.",
    )
    @app_commands.check(is_bot_owner)
    @app_commands.autocomplete(cog=cog_autocomplete)
    async def unload(
        self,
        interaction: discord.Interaction,
        cog: str,
    ):
        extension = f"bot.cogs.{cog}"

        if extension == self.__module__:
            await interaction.response.send_message(
                embed=error("The Developer cog cannot unload itself."),
                ephemeral=True,
            )
            return

        try:
            await self.bot.unload_extension(extension)
        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                embed=error(f"`{cog}` is not loaded."),
                ephemeral=True,
            )
            return
        except commands.ExtensionError as e:
            await interaction.response.send_message(
                embed=error(f"Failed to unload `{cog}`:\n`{e}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success(f"Unloaded `{cog}`."),
            ephemeral=True,
        )

    @dev.command(
        name="reload",
        description="Reload a cog.",
    )
    @app_commands.check(is_bot_owner)
    @app_commands.autocomplete(cog=cog_autocomplete)
    async def reload(
        self,
        interaction: discord.Interaction,
        cog: str,
    ):
        extension = f"bot.cogs.{cog}"

        try:
            await self.bot.reload_extension(extension)
        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                embed=error(f"`{cog}` is not loaded."),
                ephemeral=True,
            )
            return
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                embed=error(f"Cog `{cog}` was not found."),
                ephemeral=True,
            )
            return
        except commands.ExtensionError as e:
            await interaction.response.send_message(
                embed=error(f"Failed to reload `{cog}`:\n`{e}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success(f"Reloaded `{cog}`."),
            ephemeral=True,
        )

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
                embed=error("This command can only be used in a server."),
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

    @dev.command(
        name="model",
        description="Configure model storage.",
    )
    @app_commands.check(is_bot_owner)
    async def model(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        interval: app_commands.Range[int, 1, 10080],
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error("This command can only be used in a server."),
                ephemeral=True,
            )
            return

        await set_model_config(
            self.bot.db,
            interaction.guild.id,
            channel.id,
            interval * 60,
        )

        await interaction.response.send_message(
            embed=success(
                f"**Model storage** set to {channel.mention} with "
                f"**`{interval}`** minutes interval."
            ),
            ephemeral=True,
        )

    @dev.command(
        name="displayname",
        description="Change the bot's display name style.",
    )
    @app_commands.check(is_bot_owner)
    @app_commands.describe(
        font="Select a display name font",
        effect="Select a display name effect",
        color1="First color (hex, e.g. FFFFFF)",
        color2="Second color (hex, optional)",
    )
    @app_commands.choices(
        font=[
            app_commands.Choice(
                name=f"{name} ({font_id})",
                value=font_id,
            )
            for font_id, name in FONTS.items()
        ],
        effect=[
            app_commands.Choice(
                name=f"{name} ({effect_id})",
                value=effect_id,
            )
            for effect_id, name in EFFECTS.items()
        ],
    )
    async def displayname(
        self,
        interaction: discord.Interaction,
        font: app_commands.Choice[int],
        effect: app_commands.Choice[int],
        color1: str,
        color2: str | None = None,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error("This command can only be used in a server."),
                ephemeral=True,
            )
            return

        def parse_color(value: str):
            value = value.strip().replace("#", "")
            if len(value) != 6:
                raise ValueError
            return int(value, 16)

        try:
            colors = [parse_color(color1)]

            if color2:
                colors.append(parse_color(color2))
        except ValueError:
            await interaction.response.send_message(
                embed=error(
                    "Invalid color.\n"
                    "Use a 6-digit hexadecimal color such as "
                    "`FFFFFF` or `5865F2`."
                ),
                ephemeral=True,
            )
            return

        payload = {
            "display_name_font_id": font.value,
            "display_name_effect_id": effect.value,
            "display_name_colors": colors,
        }

        url = (
            "https://discord.com/api/v10"
            f"/guilds/{interaction.guild.id}/members/@me"
        )

        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json",
        }

        await interaction.response.defer(ephemeral=True)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    url,
                    headers=headers,
                    json=payload,
                ) as response:
                    text = await response.text()

                    if response.status >= 400:
                        await interaction.followup.send(
                            embed=error(
                                f"Discord returned HTTP `{response.status}`.\n"
                                f"```json\n{text[:1800]}\n```"
                            ),
                            ephemeral=True,
                        )
                        return

                    await interaction.followup.send(
                        embed=success(
                            "Display name style updated!\n\n"
                            f"**Font:** {font.name}\n"
                            f"**Effect:** {effect.name}\n"
                            f"**Colors:** "
                            f"`{', '.join(f'#{c:06X}' for c in colors)}`"
                        ),
                        ephemeral=True,
                    )

        except Exception as e:
            await interaction.followup.send(
                embed=error(f"Request failed:\n`{e}`"),
                ephemeral=True,
            )

    @dev.command(
        name="stats",
        description="Show bot statistics.",
    )
    @app_commands.check(is_bot_owner)
    async def stats(
        self,
        interaction: discord.Interaction,
    ):
        process = psutil.Process(os.getpid())

        memory = process.memory_info().rss / 1024 / 1024
        cpu = process.cpu_percent()
        latency = self.bot.latency * 1000
        uptime = int(time.monotonic() - self.bot.start_time)

        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = discord.Embed(
            title="Bot Statistics",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="Ping",
            value=f"`{latency:.0f} ms`",
            inline=True,
        )
        embed.add_field(
            name="Uptime",
            value=f"`{days}d {hours}h {minutes}m {seconds}s`",
            inline=True,
        )
        embed.add_field(
            name="Status",
            value=f"`{str(self.bot.status).title()}`",
            inline=True,
        )
        embed.add_field(
            name="CPU",
            value=f"`{cpu:.1f}%`",
            inline=True,
        )
        embed.add_field(
            name="Memory",
            value=f"`{memory:.1f} MB`",
            inline=True,
        )
        embed.add_field(
            name="Guilds",
            value=f"`{len(self.bot.guilds)}`",
            inline=True,
        )
        embed.add_field(
            name="Users",
            value=f"`{len(self.bot.users)}`",
            inline=True,
        )
        embed.add_field(
            name="Cogs",
            value=f"`{len(self.bot.cogs)}`",
            inline=True,
        )
        embed.add_field(
            name="Extensions",
            value=f"`{len(self.bot.extensions)}`",
            inline=True,
        )

        await interaction.response.send_message(
            embed=embed,
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
                embed=error("You don't have permission to use this command."),
                ephemeral=True,
            )

    @model.error
    async def model_error(
        self,
        interaction: discord.Interaction,
        exception: app_commands.AppCommandError,
    ):
        if isinstance(exception, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=error("You don't have permission to use this command."),
                ephemeral=True,
            )

    @displayname.error
    async def displayname_error(
        self,
        interaction: discord.Interaction,
        exception: app_commands.AppCommandError,
    ):
        if isinstance(exception, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=error("You don't have permission to use this command."),
                ephemeral=True,
            )

    @load.error
    async def load_error(
        self,
        interaction: discord.Interaction,
        exception: app_commands.AppCommandError,
    ):
        if isinstance(exception, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=error("You don't have permission to use this command."),
                ephemeral=True,
            )

    @unload.error
    async def unload_error(
        self,
        interaction: discord.Interaction,
        exception: app_commands.AppCommandError,
    ):
        if isinstance(exception, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=error("You don't have permission to use this command."),
                ephemeral=True,
            )

    @reload.error
    async def reload_error(
        self,
        interaction: discord.Interaction,
        exception: app_commands.AppCommandError,
    ):
        if isinstance(exception, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=error("You don't have permission to use this command."),
                ephemeral=True,
            )

    @stats.error
    async def stats_error(
        self,
        interaction: discord.Interaction,
        exception: app_commands.AppCommandError,
    ):
        if isinstance(exception, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=error("You don't have permission to use this command."),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Developer(bot))

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import get_joins_channel, set_joins_channel
from bot.utils import success, error


logger = logging.getLogger(__name__)


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(
            "Logged in as %s (%s) | Guilds: %d",
            self.bot.user,
            self.bot.user.id,
            len(self.bot.guilds),
        )

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member,
    ):
        channel_id = await get_joins_channel(
            self.bot.db,
            member.guild.id,
        )

        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)

        if channel is None:
            return

        owner = member.guild.owner

        if owner is None:
            return

        await channel.send(
            f"{owner.mention} **{member}** joined the server.",
            allowed_mentions=discord.AllowedMentions(
                users=True
            ),
        )

        logger.info(
            "Member joined | %s (%s) | Guild: %s (%s)",
            member,
            member.id,
            member.guild.name,
            member.guild.id,
        )

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        logger.error(
            "App command error | Command: %s | User: %s (%s) | Guild: %s (%s)",
            interaction.command.name
            if interaction.command
            else "Unknown",
            interaction.user,
            interaction.user.id,
            interaction.guild.name
            if interaction.guild
            else "DM",
            interaction.guild.id
            if interaction.guild
            else "N/A",
            exc_info=error,
        )

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ):
        logger.error(
            "Command error | Command: %s | User: %s (%s) | Guild: %s (%s)",
            ctx.command,
            ctx.author,
            ctx.author.id,
            ctx.guild.name
            if ctx.guild
            else "DM",
            ctx.guild.id
            if ctx.guild
            else "N/A",
            exc_info=error,
        )

    @commands.Cog.listener()
    async def on_guild_join(
        self,
        guild: discord.Guild,
    ):
        logger.info(
            "Joined guild | %s (%s) | Members: %d",
            guild.name,
            guild.id,
            guild.member_count,
        )

    @commands.Cog.listener()
    async def on_guild_remove(
        self,
        guild: discord.Guild,
    ):
        logger.warning(
            "Left guild | %s (%s)",
            guild.name,
            guild.id,
        )


class Joins(commands.GroupCog, group_name="joins"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setup",
        description="Set the channel for member join notifications.",
    )
    @app_commands.describe(
        channel="The channel where join notifications will be sent."
    )
    async def setup(
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

        if (
            interaction.user.id != interaction.guild.owner_id
            and not interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                embed=error(
                    "Only the server owner or an administrator "
                    "can use this command."
                ),
                ephemeral=True,
            )
            return

        permissions = channel.permissions_for(
            interaction.guild.me
        )

        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=error(
                    "I don't have permission to send messages "
                    f"in {channel.mention}."
                ),
                ephemeral=True,
            )
            return

        await set_joins_channel(
            self.bot.db,
            interaction.guild.id,
            channel.id,
        )

        await interaction.response.send_message(
            embed=success(
                f"Join notifications will now be sent in "
                f"{channel.mention}."
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
    await bot.add_cog(Joins(bot))
"""
Verification cog for setting up my server's verification system.
Admins or the server owner can use "/verification setup" to choose
a verification channel and configure its webhook.
This is only a Velouré server exclusive Cog.
"""

import asyncio
import random

import discord

from discord import app_commands
from discord.ext import commands

from bot.database import (
    get_verification_config,
    set_verification_config,
)
from bot.utils import success, error


VERIFICATION_ROLE_ID = 1151747087675949107

VERIFICATION_IMAGE = (
    "https://i.ibb.co/FqLw8VTm/"
    "977e7b335e707474d6184c494bf01b54.jpg"
)


class VerificationView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        self.ping_counts: dict[tuple[int, int], int] = {}

        self.container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## <a:wave:1543215898976845834>  ONBOARDING"
            ),

            discord.ui.Separator(),

            discord.ui.TextDisplay(
                "Hey! Welcome to Velouré. It is a small space for me, "
                "**@royalrizen**, to stay connected with some of my close "
                "Discord friends, mess around, and have a good time. There "
                "are very few restrictions here, so the humour and "
                "conversations can get pretty unfiltered and might not be "
                "everyone's thing. Because of that, entry is manually "
                "verified. When you join, I'll automatically get a "
                "notification to review your request. So if you're waiting "
                "for access, just be a little patient, I'll get to you lol."
            ),

            discord.ui.Separator(),

            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media=VERIFICATION_IMAGE
                )
            ),
        )

        self.buttons = discord.ui.ActionRow()

        self.why_button = discord.ui.Button(
            label="WHY??!!!",
            style=discord.ButtonStyle.secondary,
            custom_id="veloure:verification:why",
        )

        self.ping_button = discord.ui.Button(
            label="Ping Rizen",
            style=discord.ButtonStyle.primary,
            custom_id="veloure:verification:ping",
        )

        self.leave_button = discord.ui.Button(
            label="Leave Server",
            style=discord.ButtonStyle.danger,
            custom_id="veloure:verification:leave",
        )

        self.why_button.callback = self.why
        self.ping_button.callback = self.ping_rizen
        self.leave_button.callback = self.leave_server

        self.buttons.add_item(self.why_button)
        self.buttons.add_item(self.ping_button)
        self.buttons.add_item(self.leave_button)

        self.container.add_item(self.buttons)

        self.add_item(self.container)

    async def why(
        self,
        interaction: discord.Interaction,
    ):
        responses = [
            "Please read the above message carefully lol.",
            "Shut the fuck up",
            "Only for friends!",
            "Be patient.",
            "I don't like you. jkkk",
        ]

        await interaction.response.send_message(
            random.choice(responses),
            ephemeral=True,
        )

    async def ping_rizen(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.defer(
                ephemeral=True
            )
            return

        key = (
            interaction.guild.id,
            interaction.user.id,
        )

        count = self.ping_counts.get(key, 0)

        if count >= 2:
            await interaction.response.send_message(
                "You've already pinged Rizen twice.",
                ephemeral=True,
            )
            return

        self.ping_counts[key] = count + 1

        owner = interaction.guild.owner

        if owner is None:
            try:
                owner = await interaction.guild.fetch_member(
                    interaction.guild.owner_id
                )
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException,
            ):
                await interaction.response.defer(
                    ephemeral=True
                )
                return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            message = await interaction.channel.send(
                f"{owner.mention}, "
                f"||{interaction.user.mention} is asking for you.||"
            )
        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            return

        await asyncio.sleep(3)

        try:
            await message.delete()
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            pass

    async def leave_server(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.defer(
                ephemeral=True
            )
            return

        if interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Administrators cannot leave through this button.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            await interaction.guild.kick(
                interaction.user,
                reason=(
                    "User left through the Velouré "
                    "verification panel."
                ),
            )
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            return


class VerificationDoneView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=60)

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    "## Verification Setup Done"
                ),

                discord.ui.Separator(),

                discord.ui.TextDisplay(
                    "The verification panel has been "
                    "sent successfully."
                ),
            )
        )


class VerificationSetupView(discord.ui.LayoutView):
    def __init__(
        self,
        cog: "Verification",
        interaction: discord.Interaction,
    ):
        super().__init__(timeout=300)

        self.cog = cog
        self.interaction = interaction

        self.channel_id: int | None = None
        self.webhook_url: str | None = None
        self.webhook_name: str | None = None

        self.container = discord.ui.Container()

        self.title_display = discord.ui.TextDisplay(
            "## Verification Setup"
        )

        self.description_display = discord.ui.TextDisplay(
            "Configure the verification system for this server."
        )

        self.info_display = discord.ui.TextDisplay(
            self.get_info()
        )

        self.container.add_item(
            self.title_display
        )

        self.container.add_item(
            discord.ui.Separator()
        )

        self.container.add_item(
            self.description_display
        )

        self.container.add_item(
            discord.ui.Separator()
        )

        self.container.add_item(
            self.info_display
        )

        self.container.add_item(
            discord.ui.Separator()
        )

        self.channel_row = discord.ui.ActionRow()

        self.channel_select = VerificationChannelSelect(
            self
        )

        self.channel_row.add_item(
            self.channel_select
        )

        self.container.add_item(
            self.channel_row
        )

        self.button_row = discord.ui.ActionRow()

        self.create_button = CreateWebhookButton(
            self
        )

        self.create_button.disabled = True

        self.button_row.add_item(
            self.create_button
        )

        self.container.add_item(
            self.button_row
        )

        self.add_item(
            self.container
        )

    def get_info(self):
        if self.channel_id:
            channel = self.cog.bot.get_channel(
                self.channel_id
            )

            channel_value = (
                channel.mention
                if channel
                else f"<#{self.channel_id}>"
            )
        else:
            channel_value = "Not selected"

        if self.webhook_url:
            webhook_value = (
                f"[{self.webhook_name or 'Webhook'}]"
                f"({self.webhook_url})"
            )
        else:
            webhook_value = "Not configured"

        return (
            f"**Verification Channel**\n"
            f"{channel_value}\n\n"
            f"**Webhook**\n"
            f"{webhook_value}"
        )

    async def update(
        self,
        interaction: discord.Interaction,
    ):
        self.info_display.content = self.get_info()

        await interaction.response.edit_message(
            view=self
        )

    async def show_send_button(self):
        self.button_row.clear_items()

        self.button_row.add_item(
            SendVerificationButton(self)
        )

        self.info_display.content = self.get_info()

        await self.interaction.edit_original_response(
            view=self
        )

    async def create_webhook(
        self,
        interaction: discord.Interaction,
    ):
        if self.channel_id is None:
            await interaction.followup.send(
                embed=error(
                    "Please select a verification channel first."
                ),
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:
            await interaction.followup.send(
                embed=error(
                    "The selected verification channel "
                    "no longer exists."
                ),
                ephemeral=True,
            )
            return

        permissions = channel.permissions_for(
            interaction.guild.me
        )

        if not permissions.manage_webhooks:
            await interaction.followup.send(
                embed=error(
                    "I don't have permission to manage "
                    "webhooks in that channel."
                ),
                ephemeral=True,
            )
            return

        config = await get_verification_config(
            self.cog.bot.db,
            interaction.guild.id,
        )

        existing_url = None

        if config:
            existing_url = config.get(
                "verification_webhook_url"
            )

        if existing_url:
            try:
                existing_webhook = discord.Webhook.from_url(
                    existing_url,
                    client=self.cog.bot,
                )

                await existing_webhook.fetch()

            except discord.NotFound:
                await set_verification_config(
                    self.cog.bot.db,
                    interaction.guild.id,
                    self.channel_id,
                    "",
                )

            except discord.Forbidden:
                await interaction.followup.send(
                    embed=error(
                        "I don't have permission to access "
                        "the configured webhook."
                    ),
                    ephemeral=True,
                )
                return

            except discord.HTTPException as exc:
                await interaction.followup.send(
                    embed=error(
                        f"Failed to check the existing webhook: "
                        f"`{exc}`"
                    ),
                    ephemeral=True,
                )
                return

            else:
                self.webhook_url = existing_url
                self.webhook_name = existing_webhook.name

                await set_verification_config(
                    self.cog.bot.db,
                    interaction.guild.id,
                    self.channel_id,
                    self.webhook_url,
                )

                await self.show_send_button()
                return

        self.create_button.disabled = True
        self.create_button.label = "Creating..."

        self.info_display.content = self.get_info()

        await self.interaction.edit_original_response(
            view=self
        )

        try:
            avatar = None

            if interaction.guild.icon:
                try:
                    avatar = await interaction.guild.icon.read()
                except discord.HTTPException:
                    avatar = None

            webhook = await channel.create_webhook(
                name=interaction.guild.name,
                avatar=avatar,
                reason="Verification webhook setup",
            )

        except discord.Forbidden:
            self.create_button.disabled = False
            self.create_button.label = "Create Webhook"

            await self.interaction.edit_original_response(
                view=self
            )

            await interaction.followup.send(
                embed=error(
                    "I don't have permission to create "
                    "a webhook in that channel."
                ),
                ephemeral=True,
            )
            return

        except discord.HTTPException as exc:
            self.create_button.disabled = False
            self.create_button.label = "Create Webhook"

            await self.interaction.edit_original_response(
                view=self
            )

            await interaction.followup.send(
                embed=error(
                    f"Failed to create webhook: `{exc}`"
                ),
                ephemeral=True,
            )
            return

        self.webhook_url = webhook.url
        self.webhook_name = webhook.name

        await set_verification_config(
            self.cog.bot.db,
            interaction.guild.id,
            self.channel_id,
            self.webhook_url,
        )

        await self.show_send_button()

        await interaction.followup.send(
            embed=success(
                f"Webhook `{webhook.name}` created and saved."
            ),
            ephemeral=True,
        )


class VerificationChannelSelect(
    discord.ui.ChannelSelect
):
    def __init__(
        self,
        view: VerificationSetupView,
    ):
        super().__init__(
            placeholder="Select verification channel...",
            channel_types=[
                discord.ChannelType.text
            ],
            min_values=1,
            max_values=1,
        )

        self.setup_view = view

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        channel = self.values[0]

        self.setup_view.channel_id = channel.id
        self.setup_view.create_button.disabled = False

        await self.setup_view.update(
            interaction
        )


class CreateWebhookButton(
    discord.ui.Button
):
    def __init__(
        self,
        view: VerificationSetupView,
    ):
        super().__init__(
            label="Create Webhook",
            style=discord.ButtonStyle.primary,
        )

        self.setup_view = view

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        await self.setup_view.create_webhook(
            interaction
        )


class SendVerificationButton(
    discord.ui.Button
):
    def __init__(
        self,
        view: VerificationSetupView,
    ):
        super().__init__(
            label="Send",
            style=discord.ButtonStyle.primary,
        )

        self.setup_view = view

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        if self.setup_view.channel_id is None:
            await interaction.response.send_message(
                embed=error(
                    "Please select a verification channel first."
                ),
                ephemeral=True,
            )
            return

        if self.setup_view.webhook_url is None:
            await interaction.response.send_message(
                embed=error(
                    "Please create a webhook first."
                ),
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(
            self.setup_view.channel_id
        )

        if channel is None:
            await interaction.response.send_message(
                embed=error(
                    "The verification channel "
                    "no longer exists."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        await set_verification_config(
            self.setup_view.cog.bot.db,
            interaction.guild.id,
            channel.id,
            self.setup_view.webhook_url,
        )

        try:
            webhook = discord.Webhook.from_url(
                self.setup_view.webhook_url,
                client=self.setup_view.cog.bot,
            )

            await webhook.send(
                view=self.setup_view.cog.verification_view,
                wait=True,
            )

        except discord.NotFound:
            await interaction.edit_original_response(
                embed=error(
                    "The configured webhook no longer exists."
                ),
                view=None,
            )
            return

        except discord.Forbidden:
            await interaction.edit_original_response(
                embed=error(
                    "I don't have permission to use the "
                    "configured webhook."
                ),
                view=None,
            )
            return

        except discord.HTTPException as exc:
            await interaction.edit_original_response(
                embed=error(
                    f"Failed to send the verification message: "
                    f"`{exc}`"
                ),
                view=None,
            )
            return

        await interaction.edit_original_response(
            view=VerificationDoneView()
        )


class Verification(
    commands.GroupCog,
    group_name="verification",
):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot
        self.verification_view = VerificationView()

    def has_admin_access(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.guild is None:
            return False

        return (
            interaction.user.id
            == interaction.guild.owner_id
            or interaction.user.guild_permissions.administrator
        )

    @app_commands.command(
        name="setup",
        description="Set up the server verification system.",
    )
    async def setup(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error(
                    "This command can only be used "
                    "in a server."
                ),
                ephemeral=True,
            )
            return

        if not self.has_admin_access(interaction):
            await interaction.response.send_message(
                embed=error(
                    "Only the server owner or an "
                    "administrator can use this command."
                ),
                ephemeral=True,
            )
            return

        view = VerificationSetupView(
            self,
            interaction,
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

    @app_commands.command(
        name="verify",
        description="Toggle the verification role for a user.",
    )
    @app_commands.describe(
        user="The user to verify or unverify."
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error(
                    "This command can only be used "
                    "in a server."
                ),
                ephemeral=True,
            )
            return

        if not self.has_admin_access(interaction):
            await interaction.response.send_message(
                embed=error(
                    "Only the server owner or an "
                    "administrator can use this command."
                ),
                ephemeral=True,
            )
            return

        role = interaction.guild.get_role(
            VERIFICATION_ROLE_ID
        )

        if role is None:
            await interaction.response.send_message(
                embed=error(
                    "The verification role could not be found."
                ),
                ephemeral=True,
            )
            return

        bot_member = interaction.guild.me

        if bot_member is None:
            try:
                bot_member = await interaction.guild.fetch_member(
                    self.bot.user.id
                )
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException,
            ):
                await interaction.response.send_message(
                    embed=error(
                        "I could not determine my highest role."
                    ),
                    ephemeral=True,
                )
                return

        if role >= bot_member.top_role:
            await interaction.response.send_message(
                embed=error(
                    "I cannot manage this role because it is "
                    "higher than or equal to my highest role."
                ),
                ephemeral=True,
            )
            return

        try:
            if role in user.roles:
                await user.remove_roles(
                    role,
                    reason=(
                        f"Verification role removed by "
                        f"{interaction.user}."
                    ),
                )

                await interaction.response.send_message(
                    embed=success(
                        f"{user.mention} is no longer verified."
                    ),
                    ephemeral=True,
                )

            else:
                await user.add_roles(
                    role,
                    reason=(
                        f"Verified by "
                        f"{interaction.user}."
                    ),
                )

                await interaction.response.send_message(
                    embed=success(                       
                        f"{user.mention} verified."
                    ),
                    ephemeral=True,
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error(
                    "I don't have permission to manage "
                    "that user's role."
                ),
                ephemeral=True,
            )

        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error(
                    f"Failed to update the verification role: "
                    f"`{exc}`"
                ),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    verification = Verification(bot)

    bot.add_view(
        verification.verification_view
    )

    await bot.add_cog(verification)
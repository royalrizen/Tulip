import io
import re

import discord

from discord import app_commands
from discord.ext import commands

from bot.database import (
    get_skullboard_config,
    set_skullboard_config,
)
from bot.utils import success, error


SKULL_EMOJI = "💀"


class SkullboardSetupView(discord.ui.LayoutView):
    def __init__(
        self,
        cog: "Skullboard",
        interaction: discord.Interaction,
        config=None,
    ):
        super().__init__(timeout=300)

        self.cog = cog
        self.interaction = interaction

        self.channel_id: int | None = None
        self.threshold: int = 3
        self.webhook_url: str | None = None
        self.webhook_name: str | None = None

        if config:
            self.channel_id = config.get(
                "skullboard_channel_id"
            )

            self.threshold = (
                config.get("skullboard_threshold")
                or 3
            )

            self.webhook_url = config.get(
                "skullboard_webhook_url"
            )

        self.container = discord.ui.Container()

        self.container.add_item(
            discord.ui.TextDisplay(
                "## Skullboard Setup"
            )
        )

        self.container.add_item(
            discord.ui.Separator()
        )

        self.container.add_item(
            discord.ui.TextDisplay(
                "Configure the Skullboard channel and "
                "reaction threshold."
            )
        )

        self.container.add_item(
            discord.ui.Separator()
        )

        self.info_display = discord.ui.TextDisplay(
            self.get_info()
        )

        self.container.add_item(
            self.info_display
        )

        self.container.add_item(
            discord.ui.Separator()
        )

        self.channel_row = discord.ui.ActionRow()

        self.channel_select = SkullboardChannelSelect(
            self
        )

        self.channel_row.add_item(
            self.channel_select
        )

        self.container.add_item(
            self.channel_row
        )

        self.threshold_row = discord.ui.ActionRow()

        self.threshold_button = ThresholdButton(
            self
        )

        self.threshold_row.add_item(
            self.threshold_button
        )

        self.container.add_item(
            self.threshold_row
        )

        self.button_row = discord.ui.ActionRow()

        if self.webhook_url:
            self.save_button = SaveSkullboardButton(
                self
            )

            self.button_row.add_item(
                self.save_button
            )
        else:
            self.create_button = (
                CreateSkullboardWebhookButton(self)
            )

            self.create_button.disabled = (
                self.channel_id is None
            )

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

        webhook_value = (
            f"`{self.webhook_name}`"
            if self.webhook_name
            else (
                "Configured"
                if self.webhook_url
                else "Not configured"
            )
        )

        return (
            f"**Skullboard Channel**\n"
            f"{channel_value}\n\n"
            f"**Threshold**\n"
            f"{SKULL_EMOJI} {self.threshold}\n\n"
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

    async def create_webhook(
        self,
        interaction: discord.Interaction,
    ):
        if self.channel_id is None:
            await interaction.followup.send(
                embed=error(
                    "Please select a Skullboard channel first."
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
                    "The selected Skullboard channel "
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

        config = await get_skullboard_config(
            self.cog.bot.db,
            interaction.guild.id,
        )

        existing_url = None

        if config:
            existing_url = config.get(
                "skullboard_webhook_url"
            )

        if existing_url:
            try:
                webhook = discord.Webhook.from_url(
                    existing_url,
                    client=self.cog.bot,
                )

                fetched = await webhook.fetch()

            except discord.NotFound:
                existing_url = None

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
                self.webhook_name = fetched.name

                await self.finish_setup(
                    interaction
                )

                return

        self.create_button.disabled = True
        self.create_button.label = "Creating..."

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
                name="Skullboard",
                avatar=avatar,
                reason="Skullboard webhook setup",
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

        await set_skullboard_config(
            self.cog.bot.db,
            interaction.guild.id,
            self.channel_id,
            self.threshold,
            self.webhook_url,
        )

        await self.finish_setup(
            interaction
        )

        await interaction.followup.send(
            embed=success(
                f"Webhook `{webhook.name}` created and saved."
            ),
            ephemeral=True,
        )

    async def finish_setup(
        self,
        interaction: discord.Interaction,
    ):
        await set_skullboard_config(
            self.cog.bot.db,
            interaction.guild.id,
            self.channel_id,
            self.threshold,
            self.webhook_url or "",
        )

        self.info_display.content = self.get_info()

        self.button_row.clear_items()

        self.button_row.add_item(
            SaveSkullboardButton(self)
        )

        await self.interaction.edit_original_response(
            view=self
        )


class SkullboardChannelSelect(
    discord.ui.ChannelSelect
):
    def __init__(
        self,
        view: SkullboardSetupView,
    ):
        super().__init__(
            placeholder="Select Skullboard channel...",
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

        if hasattr(
            self.setup_view,
            "create_button",
        ):
            self.setup_view.create_button.disabled = False

        await self.setup_view.update(
            interaction
        )


class ThresholdModal(
    discord.ui.Modal,
    title="Skullboard Threshold",
):
    threshold = discord.ui.TextInput(
        label="Number of 💀 reactions",
        placeholder="Example: 3",
        min_length=1,
        max_length=2,
        required=True,
    )

    def __init__(
        self,
        setup_view: SkullboardSetupView,
    ):
        super().__init__()

        self.setup_view = setup_view

        self.threshold.default = str(
            setup_view.threshold
        )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        try:
            value = int(self.threshold.value)
        except ValueError:
            await interaction.response.send_message(
                embed=error(
                    "The threshold must be a number."
                ),
                ephemeral=True,
            )
            return

        if value < 1:
            await interaction.response.send_message(
                embed=error(
                    "The threshold must be at least 1."
                ),
                ephemeral=True,
            )
            return

        if value > 99:
            await interaction.response.send_message(
                embed=error(
                    "The threshold cannot be greater than 99."
                ),
                ephemeral=True,
            )
            return

        self.setup_view.threshold = value

        self.setup_view.info_display.content = (
            self.setup_view.get_info()
        )

        await interaction.response.edit_message(
            view=self.setup_view
        )


class ThresholdButton(
    discord.ui.Button
):
    def __init__(
        self,
        view: SkullboardSetupView,
    ):
        super().__init__(
            label="Set Threshold",
            style=discord.ButtonStyle.secondary,
        )

        self.setup_view = view

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.send_modal(
            ThresholdModal(self.setup_view)
        )


class CreateSkullboardWebhookButton(
    discord.ui.Button
):
    def __init__(
        self,
        view: SkullboardSetupView,
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
        await interaction.response.defer(
            ephemeral=True
        )

        await self.setup_view.create_webhook(
            interaction
        )


class SaveSkullboardButton(
    discord.ui.Button
):
    def __init__(
        self,
        view: SkullboardSetupView,
    ):
        super().__init__(
            label="Save",
            style=discord.ButtonStyle.success,
        )

        self.setup_view = view

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        if self.setup_view.channel_id is None:
            await interaction.response.send_message(
                embed=error(
                    "Please select a Skullboard channel first."
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

        try:
            webhook = discord.Webhook.from_url(
                self.setup_view.webhook_url,
                client=self.setup_view.cog.bot,
            )

            fetched = await webhook.fetch()

            self.setup_view.webhook_name = fetched.name

        except discord.NotFound:
            self.setup_view.webhook_url = None

            await interaction.response.send_message(
                embed=error(
                    "The configured webhook no longer exists. "
                    "Please run setup again to create a new one."
                ),
                ephemeral=True,
            )
            return

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error(
                    "I don't have permission to access "
                    "the configured webhook."
                ),
                ephemeral=True,
            )
            return

        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error(
                    f"Failed to check the webhook: `{exc}`"
                ),
                ephemeral=True,
            )
            return

        await set_skullboard_config(
            self.setup_view.cog.bot.db,
            interaction.guild.id,
            self.setup_view.channel_id,
            self.setup_view.threshold,
            self.setup_view.webhook_url,
        )

        await interaction.response.edit_message(
            view=SkullboardDoneView()
        )


class SkullboardDoneView(
    discord.ui.LayoutView
):
    def __init__(self):
        super().__init__(timeout=60)

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    "## Skullboard Setup Done"
                ),

                discord.ui.Separator(),

                discord.ui.TextDisplay(
                    "The Skullboard system has been "
                    "configured successfully."
                ),
            )
        )


class Skullboard(
    commands.GroupCog,
    group_name="skullboard",
):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot
        self.skullboarded_messages: set[int] = set()

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

    @staticmethod
    def sanitize_content(
        content: str,
    ) -> str:
        """Remove Discord mention tokens from Skullboard content."""
        return re.sub(
            r"@everyone|@here|<@!?\d+>|<@&\d+>",
            "",
            content,
        )

    @app_commands.command(
        name="setup",
        description="Set up or edit the server Skullboard system.",
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

        config = await get_skullboard_config(
            self.bot.db,
            interaction.guild.id,
        )

        view = SkullboardSetupView(
            self,
            interaction,
            config=config,
        )

        if config:
            webhook_url = config.get(
                "skullboard_webhook_url"
            )

            if webhook_url:
                try:
                    webhook = discord.Webhook.from_url(
                        webhook_url,
                        client=self.bot,
                    )

                    fetched = await webhook.fetch()

                    view.webhook_name = fetched.name

                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    view.webhook_url = None

                    view.button_row.clear_items()

                    view.create_button = (
                        CreateSkullboardWebhookButton(view)
                    )

                    view.create_button.disabled = (
                        view.channel_id is None
                    )

                    view.button_row.add_item(
                        view.create_button
                    )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

    @app_commands.command(
        name="disable",
        description="Disable Skullboard for this server.",
    )
    async def disable(
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

        config = await get_skullboard_config(
            self.bot.db,
            interaction.guild.id,
        )

        if not config:
            await interaction.response.send_message(
                embed=error(
                    "Skullboard is not configured "
                    "for this server."
                ),
                ephemeral=True,
            )
            return

        webhook_url = config.get(
            "skullboard_webhook_url"
        )

        if webhook_url:
            try:
                webhook = discord.Webhook.from_url(
                    webhook_url,
                    client=self.bot,
                )

                await webhook.delete(
                    reason="Skullboard disabled"
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException,
            ):
                pass

        await set_skullboard_config(
            self.bot.db,
            interaction.guild.id,
            None,
            0,
            "",
        )

        self.skullboarded_messages.clear()

        await interaction.response.send_message(
            embed=success(
                "Skullboard has been disabled."
            ),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent,
    ):
        if payload.guild_id is None:
            return

        if str(payload.emoji) != SKULL_EMOJI:
            return

        config = await get_skullboard_config(
            self.bot.db,
            payload.guild_id,
        )

        if not config:
            return

        skull_channel_id = config.get(
            "skullboard_channel_id"
        )

        threshold = config.get(
            "skullboard_threshold"
        )

        webhook_url = config.get(
            "skullboard_webhook_url"
        )

        if not skull_channel_id:
            return

        if not threshold:
            return

        if not webhook_url:
            return

        if payload.channel_id == skull_channel_id:
            return

        if payload.message_id in self.skullboarded_messages:
            return

        channel = self.bot.get_channel(
            payload.channel_id
        )

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    payload.channel_id
                )
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException,
            ):
                return

        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            return

        try:
            message = await channel.fetch_message(
                payload.message_id
            )
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            return

        skull_reaction = next(
            (
                reaction
                for reaction in message.reactions
                if str(reaction.emoji) == SKULL_EMOJI
            ),
            None,
        )

        if skull_reaction is None:
            return

        skull_count = skull_reaction.count

        if skull_count < threshold:
            return

        if message.id in self.skullboarded_messages:
            return

        self.skullboarded_messages.add(
            message.id
        )

        try:
            skull_channel = self.bot.get_channel(
                skull_channel_id
            )

            if skull_channel is None:
                try:
                    skull_channel = (
                        await self.bot.fetch_channel(
                            skull_channel_id
                        )
                    )
                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    return

            if not isinstance(
                skull_channel,
                discord.TextChannel,
            ):
                return

            webhook = discord.Webhook.from_url(
                webhook_url,
                client=self.bot,
            )

            username = message.author.display_name

            avatar_url = (
                message.author.display_avatar.url
            )

            content = self.sanitize_content(
                message.content
            ).strip()

            if len(content) > 1900:
                content = content[:1897] + "..."

            files: list[discord.File] = []

            for attachment in message.attachments:
                try:
                    data = await attachment.read(
                        use_cached=True
                    )

                    files.append(
                        discord.File(
                            io.BytesIO(data),
                            filename=attachment.filename,
                            description=attachment.description,
                        )
                    )

                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    pass

            view = discord.ui.View(
                timeout=None
            )

            view.add_item(
                discord.ui.Button(
                    label=channel.name,
                    emoji=SKULL_EMOJI,
                    style=discord.ButtonStyle.link,
                    url=message.jump_url,
                )
            )

            await webhook.send(
                content=content,
                username=username,
                avatar_url=avatar_url,
                files=files,
                view=view,
                allowed_mentions=discord.AllowedMentions.none(),
                wait=True,
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            pass


async def setup(
    bot: commands.Bot,
):
    skullboard = Skullboard(bot)

    await bot.add_cog(
        skullboard
    )

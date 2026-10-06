import io
import random
import re
import discord
from discord import app_commands
from discord.ext import commands
from bot.database import get_skullboard_config, set_skullboard_config
from bot.utils import success, error

SKULL_EMOJI = "💀"


class SkullboardSetupView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(label="Select Channel", style=discord.ButtonStyle.primary)
    async def channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        channels = [
            c for c in interaction.guild.text_channels
            if c.permissions_for(interaction.guild.me).send_messages
        ]
        if not channels:
            return await interaction.response.send_message(
                error("No usable text channels found."),
                ephemeral=True
            )
        view = discord.ui.View(timeout=300)
        select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Select the skullboard channel"
        )

        async def callback(inter: discord.Interaction):
            channel = select.values[0]
            await set_skullboard_config(self.guild_id, "skullboard_channel_id", channel.id)
            await inter.response.edit_message(
                content=None,
                embed=success(f"Skullboard channel set to {channel.mention}."),
                view=None
            )

        select.callback = callback
        view.add_item(select)
        await interaction.response.send_message(
            "Select the skullboard channel:",
            view=view,
            ephemeral=True
        )


class SkullboardMessageView(discord.ui.View):
    def __init__(self, message: discord.Message, channel_name: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label=channel_name,
            emoji=SKULL_EMOJI,
            style=discord.ButtonStyle.link,
            url=message.jump_url
        ))


class Skullboard(commands.GroupCog, group_name="skullboard"):
    def __init__(self, bot):
        self.bot = bot
        self.skullboarded_messages = set()

    def sanitize_content(self, content):
        content = re.sub(r"@everyone|@here", "", content, flags=re.IGNORECASE)
        content = re.sub(r"<@!?\d+>", "", content)
        content = re.sub(r"<@&\d+>", "", content)
        return content.strip()

    def build_message_content(self, message):
        content = self.sanitize_content(message.content or "")
        if len(content) > 1900:
            content = content[:1897] + "..."
        return content

    async def download_attachments(self, message):
        files = []
        for attachment in message.attachments:
            try:
                data = await attachment.read()
                files.append(discord.File(io.BytesIO(data), filename=attachment.filename))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue
        return files

    async def download_stickers(self, message):
        files = []
        names = []

        for index, sticker in enumerate(message.stickers):
            try:
                url = sticker.url
                data = await url.read()
                filename = f"sticker_{index}.png"
                files.append(discord.File(io.BytesIO(data), filename=filename))
                names.append(filename)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue
            except Exception:
                continue

        return files, names

    def attachment_gallery(self, filenames):
        if not filenames:
            return None

        gallery = discord.ui.MediaGallery()
        for filename in filenames:
            gallery.add_item(
                discord.MediaGalleryItem(
                    media=f"attachment://{filename}"
                )
            )
        return gallery

    def url_gallery(self, urls):
        if not urls:
            return None

        gallery = discord.ui.MediaGallery()
        for url in urls:
            gallery.add_item(
                discord.MediaGalleryItem(media=url)
            )
        return gallery

    def build_random_components(self, message):
        container = discord.ui.Container()

        content = self.build_message_content(message)
        if content:
            container.add_item(discord.ui.TextDisplay(content))

        if message.attachments:
            gallery = self.url_gallery([a.url for a in message.attachments])
            if gallery:
                container.add_item(gallery)

        if message.stickers:
            sticker_urls = []
            for sticker in message.stickers:
                try:
                    url = str(sticker.url)
                    if url and not url.endswith(".json"):
                        sticker_urls.append(url)
                except Exception:
                    continue

            gallery = self.url_gallery(sticker_urls)
            if gallery:
                container.add_item(discord.ui.TextDisplay("### Sticker"))
                container.add_item(gallery)

        container.add_item(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="Jump to Message",
                    style=discord.ButtonStyle.link,
                    url=message.jump_url
                )
            )
        )

        view = discord.ui.LayoutView()
        view.add_item(container)
        return view

    async def build_sticker_components(self, message):
        files, filenames = await self.download_stickers(message)
        if not files:
            return None, []

        container = discord.ui.Container()

        content = self.build_message_content(message)
        if content:
            container.add_item(discord.ui.TextDisplay(content))

        container.add_item(discord.ui.TextDisplay("### Sticker"))

        gallery = self.attachment_gallery(filenames)
        if gallery:
            container.add_item(gallery)

        container.add_item(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="Jump to Message",
                    style=discord.ButtonStyle.link,
                    url=message.jump_url
                )
            )
        )

        view = discord.ui.LayoutView()
        view.add_item(container)
        return view, files

    @app_commands.command(name="setup", description="Set up the skullboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction):
        config = await get_skullboard_config(interaction.guild.id)

        if not config.get("skullboard_threshold"):
            await set_skullboard_config(
                interaction.guild.id,
                "skullboard_threshold",
                3
            )

        await interaction.response.send_message(
            embed=success("Choose the channel where skullboard messages should be sent."),
            view=SkullboardSetupView(self, interaction.guild.id),
            ephemeral=True
        )

    @app_commands.command(name="disable", description="Disable the skullboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction):
        await set_skullboard_config(
            interaction.guild.id,
            "skullboard_channel_id",
            None
        )
        await set_skullboard_config(
            interaction.guild.id,
            "skullboard_webhook_url",
            None
        )
        await interaction.response.send_message(
            embed=success("Skullboard has been disabled."),
            ephemeral=True
        )

    @app_commands.command(name="random", description="Send a random skullboard message.")
    async def random(self, interaction: discord.Interaction):
        config = await get_skullboard_config(interaction.guild.id)
        channel_id = config.get("skullboard_channel_id")

        if not channel_id:
            return await interaction.response.send_message(
                embed=error("Skullboard is not configured."),
                ephemeral=True
            )

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            return await interaction.response.send_message(
                embed=error("The configured skullboard channel no longer exists."),
                ephemeral=True
            )

        messages = [m async for m in channel.history(limit=100)]
        if not messages:
            return await interaction.response.send_message(
                embed=error("There are no skullboard messages."),
                ephemeral=True
            )

        message = random.choice(messages)

        await interaction.response.defer()

        view = self.build_random_components(message)

        await interaction.followup.send(view=view)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != SKULL_EMOJI:
            return

        if payload.guild_id is None:
            return

        config = await get_skullboard_config(payload.guild_id)
        channel_id = config.get("skullboard_channel_id")
        threshold = config.get("skullboard_threshold", 3)
        webhook_url = config.get("skullboard_webhook_url")

        if not channel_id or not webhook_url:
            return

        if payload.channel_id == channel_id:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

        reaction = discord.utils.get(message.reactions, emoji=SKULL_EMOJI)
        if reaction is None or reaction.count < threshold:
            return

        if message.id in self.skullboarded_messages:
            return

        self.skullboarded_messages.add(message.id)

        try:
            webhook = discord.Webhook.from_url(
                webhook_url,
                session=self.bot.http._HTTPClient__session
            )

            if message.stickers:
                view, files = await self.build_sticker_components(message)

                if view is None:
                    self.skullboarded_messages.discard(message.id)
                    return

                await webhook.send(
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar.url,
                    files=files,
                    view=view,
                    allowed_mentions=discord.AllowedMentions.none(),
                    wait=True
                )
            else:
                files = await self.download_attachments(message)
                content = self.build_message_content(message)
                view = SkullboardMessageView(message, channel.name)

                await webhook.send(
                    content=content or None,
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar.url,
                    files=files,
                    view=view,
                    allowed_mentions=discord.AllowedMentions.none(),
                    wait=True
                )

        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            self.skullboarded_messages.discard(message.id)
        except Exception:
            self.skullboarded_messages.discard(message.id)


async def setup(bot):
    await bot.add_cog(Skullboard(bot))

import re
import discord
from discord import app_commands
from discord.ext import commands
from bot.database import get_skullboard_config,set_skullboard_config
from bot.utils import success,error

SKULL_EMOJI="💀"

class SkullboardSetupView(discord.ui.LayoutView):
    def __init__(self,cog,interaction,config=None):
        super().__init__(timeout=300)
        self.cog=cog
        self.interaction=interaction
        self.channel_id=config.get("skullboard_channel_id") if config else None
        self.threshold=(config.get("skullboard_threshold") or 3) if config else 3
        self.webhook_url=config.get("skullboard_webhook_url") if config else None
        self.webhook_name=None
        self.container=discord.ui.Container(
            discord.ui.TextDisplay("## Skullboard Setup"),
            discord.ui.Separator(),
            discord.ui.TextDisplay("Configure the Skullboard channel and reaction threshold."),
            discord.ui.Separator()
        )
        self.info_display=discord.ui.TextDisplay(self.get_info())
        self.container.add_item(self.info_display)
        self.container.add_item(discord.ui.Separator())
        self.channel_row=discord.ui.ActionRow()
        self.channel_select=SkullboardChannelSelect(self)
        self.channel_row.add_item(self.channel_select)
        self.container.add_item(self.channel_row)
        self.threshold_row=discord.ui.ActionRow()
        self.threshold_button=ThresholdButton(self)
        self.threshold_row.add_item(self.threshold_button)
        self.container.add_item(self.threshold_row)
        self.button_row=discord.ui.ActionRow()
        if self.webhook_url:
            self.button_row.add_item(SaveSkullboardButton(self))
        else:
            self.create_button=CreateSkullboardWebhookButton(self)
            self.create_button.disabled=self.channel_id is None
            self.button_row.add_item(self.create_button)
        self.container.add_item(self.button_row)
        self.add_item(self.container)

    def get_info(self):
        channel=self.cog.bot.get_channel(self.channel_id) if self.channel_id else None
        channel_value=channel.mention if channel else (f"<#{self.channel_id}>" if self.channel_id else "Not selected")
        webhook_value=f"`{self.webhook_name}`" if self.webhook_name else ("Configured" if self.webhook_url else "Not configured")
        return f"**Skullboard Channel**\n{channel_value}\n\n**Threshold**\n{SKULL_EMOJI} {self.threshold}\n\n**Webhook**\n{webhook_value}"

    async def update(self,interaction):
        self.info_display.content=self.get_info()
        await interaction.response.edit_message(view=self)

    async def create_webhook(self,interaction):
        if self.channel_id is None:
            return await interaction.followup.send(embed=error("Please select a Skullboard channel first."),ephemeral=True)
        channel=interaction.guild.get_channel(self.channel_id)
        if channel is None:
            return await interaction.followup.send(embed=error("The selected Skullboard channel no longer exists."),ephemeral=True)
        permissions=channel.permissions_for(interaction.guild.me)
        if not permissions.manage_webhooks:
            return await interaction.followup.send(embed=error("I don't have permission to manage webhooks in that channel."),ephemeral=True)
        config=await get_skullboard_config(self.cog.bot.db,interaction.guild.id)
        existing_url=config.get("skullboard_webhook_url") if config else None
        if existing_url:
            try:
                webhook=discord.Webhook.from_url(existing_url,client=self.cog.bot)
                fetched=await webhook.fetch()
                self.webhook_url=existing_url
                self.webhook_name=fetched.name
                await self.finish_setup(interaction)
                return
            except discord.NotFound:
                self.webhook_url=None
            except discord.Forbidden:
                return await interaction.followup.send(embed=error("I don't have permission to access the configured webhook."),ephemeral=True)
            except discord.HTTPException as exc:
                return await interaction.followup.send(embed=error(f"Failed to check the existing webhook: `{exc}`"),ephemeral=True)
        self.create_button.disabled=True
        self.create_button.label="Creating..."
        await self.interaction.edit_original_response(view=self)
        try:
            avatar=None
            if interaction.guild.icon:
                try:
                    avatar=await interaction.guild.icon.read()
                except discord.HTTPException:
                    pass
            webhook=await channel.create_webhook(name="Skullboard",avatar=avatar,reason="Skullboard webhook setup")
        except discord.Forbidden:
            self.create_button.disabled=False
            self.create_button.label="Create Webhook"
            await self.interaction.edit_original_response(view=self)
            return await interaction.followup.send(embed=error("I don't have permission to create a webhook in that channel."),ephemeral=True)
        except discord.HTTPException as exc:
            self.create_button.disabled=False
            self.create_button.label="Create Webhook"
            await self.interaction.edit_original_response(view=self)
            return await interaction.followup.send(embed=error(f"Failed to create webhook: `{exc}`"),ephemeral=True)
        self.webhook_url=webhook.url
        self.webhook_name=webhook.name
        await set_skullboard_config(self.cog.bot.db,interaction.guild.id,self.channel_id,self.threshold,self.webhook_url)
        await self.finish_setup(interaction)
        await interaction.followup.send(embed=success(f"Webhook `{webhook.name}` created and saved."),ephemeral=True)

    async def finish_setup(self,interaction):
        await set_skullboard_config(self.cog.bot.db,interaction.guild.id,self.channel_id,self.threshold,self.webhook_url or "")
        self.info_display.content=self.get_info()
        self.button_row.clear_items()
        self.button_row.add_item(SaveSkullboardButton(self))
        await self.interaction.edit_original_response(view=self)

class SkullboardChannelSelect(discord.ui.ChannelSelect):
    def __init__(self,view):
        super().__init__(placeholder="Select Skullboard channel...",channel_types=[discord.ChannelType.text],min_values=1,max_values=1)
        self.setup_view=view

    async def callback(self,interaction):
        self.setup_view.channel_id=self.values[0].id
        if hasattr(self.setup_view,"create_button"):
            self.setup_view.create_button.disabled=False
        await self.setup_view.update(interaction)

class ThresholdModal(discord.ui.Modal,title="Skullboard Threshold"):
    threshold=discord.ui.TextInput(label="Number of 💀 reactions",placeholder="Example: 3",min_length=1,max_length=2,required=True)

    def __init__(self,setup_view):
        super().__init__()
        self.setup_view=setup_view
        self.threshold.default=str(setup_view.threshold)

    async def on_submit(self,interaction):
        try:
            value=int(self.threshold.value)
        except ValueError:
            return await interaction.response.send_message(embed=error("The threshold must be a number."),ephemeral=True)
        if value<1:
            return await interaction.response.send_message(embed=error("The threshold must be at least 1."),ephemeral=True)
        if value>99:
            return await interaction.response.send_message(embed=error("The threshold cannot be greater than 99."),ephemeral=True)
        self.setup_view.threshold=value
        self.setup_view.info_display.content=self.setup_view.get_info()
        await interaction.response.edit_message(view=self.setup_view)

class ThresholdButton(discord.ui.Button):
    def __init__(self,view):
        super().__init__(label="Set Threshold",style=discord.ButtonStyle.secondary)
        self.setup_view=view

    async def callback(self,interaction):
        await interaction.response.send_modal(ThresholdModal(self.setup_view))

class CreateSkullboardWebhookButton(discord.ui.Button):
    def __init__(self,view):
        super().__init__(label="Create Webhook",style=discord.ButtonStyle.primary)
        self.setup_view=view

    async def callback(self,interaction):
        await interaction.response.defer(ephemeral=True)
        await self.setup_view.create_webhook(interaction)

class SaveSkullboardButton(discord.ui.Button):
    def __init__(self,view):
        super().__init__(label="Save",style=discord.ButtonStyle.success)
        self.setup_view=view

    async def callback(self,interaction):
        if self.setup_view.channel_id is None:
            return await interaction.response.send_message(embed=error("Please select a Skullboard channel first."),ephemeral=True)
        if self.setup_view.webhook_url is None:
            return await interaction.response.send_message(embed=error("Please create a webhook first."),ephemeral=True)
        try:
            webhook=discord.Webhook.from_url(self.setup_view.webhook_url,client=self.setup_view.cog.bot)
            fetched=await webhook.fetch()
            self.setup_view.webhook_name=fetched.name
        except discord.NotFound:
            self.setup_view.webhook_url=None
            return await interaction.response.send_message(embed=error("The configured webhook no longer exists. Please run setup again to create a new one."),ephemeral=True)
        except discord.Forbidden:
            return await interaction.response.send_message(embed=error("I don't have permission to access the configured webhook."),ephemeral=True)
        except discord.HTTPException as exc:
            return await interaction.response.send_message(embed=error(f"Failed to check the webhook: `{exc}`"),ephemeral=True)
        await set_skullboard_config(self.setup_view.cog.bot.db,interaction.guild.id,self.setup_view.channel_id,self.setup_view.threshold,self.setup_view.webhook_url)
        await interaction.response.edit_message(view=SkullboardDoneView())

class SkullboardDoneView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(discord.ui.Container(discord.ui.TextDisplay("## Skullboard Setup Done"),discord.ui.Separator(),discord.ui.TextDisplay("The Skullboard system has been configured successfully.")))

class Skullboard(commands.GroupCog,group_name="skullboard"):
    def __init__(self,bot):
        self.bot=bot
        self.skullboarded_messages=set()

    def has_admin_access(self,interaction):
        return interaction.guild is not None and (interaction.user.id==interaction.guild.owner_id or interaction.user.guild_permissions.administrator)

    @staticmethod
    def sanitize_content(content):
        if not content:
            return ""
        content=re.sub(r"@everyone|@here","",content,flags=re.IGNORECASE)
        content=re.sub(r"<@!?\d+>","",content)
        content=re.sub(r"<@&\d+>","",content)
        return content

    @classmethod
    def build_message_content(cls,message):
        content=cls.sanitize_content(message.content).strip()
        if len(content)>2000:
            content=content[:1997]+"..."
        return content

    @staticmethod
    async def download_attachments(message):
        files=[]
        for attachment in message.attachments:
            try:
                data=await attachment.read(use_cached=True)
                files.append(discord.File(io.BytesIO(data),filename=attachment.filename,description=attachment.description))
            except (discord.NotFound,discord.Forbidden,discord.HTTPException):
                continue
        return files

    @staticmethod
    def make_gallery(urls):
        if not urls:
            return None
        gallery=discord.ui.MediaGallery()
        for url in urls:
            gallery.add_item(media=url)
        return gallery

    def build_random_view(self,message):
        container=discord.ui.Container()
        content=self.build_message_content(message)
        if content:
            container.add_item(discord.ui.TextDisplay(content))
        attachment_urls=[a.url for a in message.attachments]
        if attachment_urls:
            gallery=self.make_gallery(attachment_urls)
            if gallery:
                container.add_item(gallery)
        sticker_urls=[]
        for sticker in message.stickers:
            try:
                url=str(sticker.url)
                if url and not url.endswith(".json"):
                    sticker_urls.append(url)
            except Exception:
                pass
        if sticker_urls:
            container.add_item(discord.ui.TextDisplay("### Sticker"))
            gallery=self.make_gallery(sticker_urls)
            if gallery:
                container.add_item(gallery)
        container.add_item(discord.ui.ActionRow(discord.ui.Button(label="Jump to Message",style=discord.ButtonStyle.link,url=message.jump_url)))
        view=discord.ui.LayoutView()
        view.add_item(container)
        return view

    def build_sticker_view(self,message):
        container=discord.ui.Container()
        content=self.build_message_content(message)
        if content:
            container.add_item(discord.ui.TextDisplay(content))
        urls=[]
        for sticker in message.stickers:
            try:
                url=str(sticker.url)
                if url and not url.endswith(".json"):
                    urls.append(url)
            except Exception:
                pass
        if urls:
            container.add_item(discord.ui.TextDisplay("### Sticker"))
            gallery=self.make_gallery(urls)
            if gallery:
                container.add_item(gallery)
        container.add_item(discord.ui.ActionRow(discord.ui.Button(label="Jump to Message",style=discord.ButtonStyle.link,url=message.jump_url)))
        view=discord.ui.LayoutView()
        view.add_item(container)
        return view

    @app_commands.command(name="setup",description="Set up or edit the server Skullboard system.")
    async def setup(self,interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(embed=error("This command can only be used in a server."),ephemeral=True)
        if not self.has_admin_access(interaction):
            return await interaction.response.send_message(embed=error("Only the server owner or an administrator can configure Skullboard."),ephemeral=True)
        config=await get_skullboard_config(self.bot.db,interaction.guild.id)
        view=SkullboardSetupView(self,interaction,config)
        if view.webhook_url:
            try:
                webhook=discord.Webhook.from_url(view.webhook_url,client=self.bot)
                fetched=await webhook.fetch()
                view.webhook_name=fetched.name
            except (discord.NotFound,discord.Forbidden,discord.HTTPException):
                pass
        await interaction.response.send_message(view=view,ephemeral=True)

    @app_commands.command(name="disable",description="Disable Skullboard for this server.")
    async def disable(self,interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(embed=error("This command can only be used in a server."),ephemeral=True)
        if not self.has_admin_access(interaction):
            return await interaction.response.send_message(embed=error("Only the server owner or an administrator can disable Skullboard."),ephemeral=True)
        config=await get_skullboard_config(self.bot.db,interaction.guild.id)
        if config and config.get("skullboard_webhook_url"):
            try:
                webhook=discord.Webhook.from_url(config["skullboard_webhook_url"],client=self.bot)
                await webhook.delete(reason="Skullboard disabled")
            except (discord.NotFound,discord.Forbidden,discord.HTTPException):
                pass
        await set_skullboard_config(self.bot.db,interaction.guild.id,None,0,"")
        self.skullboarded_messages.clear()
        await interaction.response.send_message(embed=success("Skullboard has been disabled for this server."),ephemeral=True)

    @app_commands.command(name="random",description="Send a random skullboard message.")
    async def random(self,interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(embed=error("This command can only be used in a server."),ephemeral=True)
        config=await get_skullboard_config(self.bot.db,interaction.guild.id)
        channel_id=config.get("skullboard_channel_id") if config else None
        if not channel_id:
            return await interaction.response.send_message(embed=error("Skullboard is not configured."),ephemeral=True)
        channel=self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel=await self.bot.fetch_channel(channel_id)
            except (discord.NotFound,discord.Forbidden,discord.HTTPException):
                return await interaction.response.send_message(embed=error("The configured Skullboard channel no longer exists."),ephemeral=True)
        if not isinstance(channel,discord.TextChannel):
            return await interaction.response.send_message(embed=error("The configured Skullboard channel is invalid."),ephemeral=True)
        await interaction.response.defer()
        messages=[m async for m in channel.history(limit=100)]
        if not messages:
            return await interaction.followup.send(embed=error("There are no Skullboard messages."))
        message=__import__("random").choice(messages)
        await interaction.followup.send(view=self.build_random_view(message))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        message=None
        channel=None
        try:
            if payload.guild_id is None or str(payload.emoji)!=SKULL_EMOJI:
                return
            config=await get_skullboard_config(self.bot.db,payload.guild_id)
            if not config:
                return
            skull_channel_id=config.get("skullboard_channel_id")
            threshold=config.get("skullboard_threshold")
            webhook_url=config.get("skullboard_webhook_url")
            if not skull_channel_id or not threshold or not webhook_url:
                return
            if payload.channel_id==skull_channel_id or payload.message_id in self.skullboarded_messages:
                return
            channel=self.bot.get_channel(payload.channel_id)
            if channel is None:
                channel=await self.bot.fetch_channel(payload.channel_id)
            if not isinstance(channel,discord.TextChannel):
                return
            message=await channel.fetch_message(payload.message_id)
            reaction=next((r for r in message.reactions if str(r.emoji)==SKULL_EMOJI),None)
            if reaction is None or reaction.count<threshold:
                return
            skull_channel=self.bot.get_channel(skull_channel_id)
            if skull_channel is None:
                skull_channel=await self.bot.fetch_channel(skull_channel_id)
            if not isinstance(skull_channel,discord.TextChannel):
                return
            webhook=discord.Webhook.from_url(webhook_url,client=self.bot)
            self.skullboarded_messages.add(message.id)
            if message.stickers:
                view=self.build_sticker_view(message)
                has_sticker=any(str(s.url) and not str(s.url).endswith(".json") for s in message.stickers)
                if not has_sticker:
                    self.skullboarded_messages.discard(message.id)
                    return
                await webhook.send(username=message.author.display_name,avatar_url=message.author.display_avatar.url,view=view,allowed_mentions=discord.AllowedMentions.none(),wait=True)
                return
            content=self.build_message_content(message)
            files=await self.download_attachments(message)
            if not content and not files:
                self.skullboarded_messages.discard(message.id)
                return
            view=discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label=channel.name,emoji=SKULL_EMOJI,style=discord.ButtonStyle.link,url=message.jump_url))
            await webhook.send(content=content or None,username=message.author.display_name,avatar_url=message.author.display_avatar.url,files=files,view=view,allowed_mentions=discord.AllowedMentions.none(),wait=True)
        except Exception as exc:
            if message:
                self.skullboarded_messages.discard(message.id)
            if channel:
                try:
                    await channel.send(embed=error(f"Skullboard error: `{type(exc).__name__}: {str(exc)[:1500]}`"),allowed_mentions=discord.AllowedMentions.none())
                except Exception:
                    pass

async def setup(bot):
    await bot.add_cog(Skullboard(bot))

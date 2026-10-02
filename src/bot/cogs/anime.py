import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from bot.utils import error

class AnimeResultView(discord.ui.LayoutView):
    def __init__(self, title: str, native_title: str, similarity: float, episode, from_time: float, to_time: float, is_adult: bool, image_url: str, video_url: str | None):
        super().__init__(timeout=300)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"## 🎬 {title}\n### {native_title}"))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            f"**Similarity**\n`{similarity:.2f}%`\n\n"
            f"**Episode**\n`{episode}`\n\n"
            f"**Timestamp**\n`{from_time:.2f}s` → `{to_time:.2f}s`\n\n"
            f"**NSFW**\n`{'Yes' if is_adult else 'No'}`"
        ))
        container.add_item(discord.ui.Separator())

        if image_url:
            container.add_item(discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media=image_url,
                    description=f"{title} scene"
                )
            ))

        if video_url:
            container.add_item(discord.ui.Separator())
            row = discord.ui.ActionRow()
            row.add_item(discord.ui.Button(
                label="Watch Scene",
                style=discord.ButtonStyle.link,
                url=video_url,
                emoji="🎥"
            ))
            container.add_item(row)

        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay("-# Powered by trace.moe"))
        self.add_item(container)

class Anime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="anime", description="Search anime from an image.")
    async def trace_anime(self, interaction: discord.Interaction, image: discord.Attachment):
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.response.send_message(
                embed=error("Please upload a valid image."),
                ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            image_data = await image.read()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.trace.moe/search?anilistInfo",
                    data=image_data,
                    headers={"Content-Type": image.content_type}
                ) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            embed=error("Failed to retrieve anime data. Please try again later."),
                            ephemeral=True
                        )
                        return

                    data = await response.json()

        except aiohttp.ClientError:
            await interaction.followup.send(
                embed=error("Failed to connect to the anime search service."),
                ephemeral=True
            )
            return
        except Exception:
            await interaction.followup.send(
                embed=error("Something went wrong while processing the image."),
                ephemeral=True
            )
            return

        results = data.get("result", [])

        if not results:
            await interaction.followup.send(
                embed=error("No matching anime found."),
                ephemeral=True
            )
            return

        result = results[0]
        anilist_info = result.get("anilist", {})
        titles = anilist_info.get("title", {})

        title = titles.get("romaji", "Unknown")
        native_title = titles.get("native", "N/A")
        is_adult = anilist_info.get("isAdult", False)
        episode = result.get("episode", "N/A")
        similarity = result.get("similarity", 0) * 100
        from_time = result.get("from", 0)
        to_time = result.get("to", 0)
        image_url = result.get("image")
        video_url = result.get("video")

        view = AnimeResultView(
            title=title,
            native_title=native_title,
            similarity=similarity,
            episode=episode,
            from_time=from_time,
            to_time=to_time,
            is_adult=is_adult,
            image_url=image_url,
            video_url=video_url
        )

        await interaction.followup.send(view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Anime(bot))

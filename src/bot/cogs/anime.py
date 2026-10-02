import discord
from discord.ext import commands
from discord import app_commands as s
import requests
import config

class Anime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @s.command(name="anime", description="Search anime from an image")
    async def trace_anime(self, interaction: discord.Interaction, image: discord.Attachment):
        image_data = await image.read()
        response = requests.post(
            "https://api.trace.moe/search?anilistInfo",
            data=image_data,
            headers={"Content-Type": "image/jpeg"}
        )

        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data['result'], list) and data['result']:
                result = data['result'][0]
                anilist_info = result['anilist']
                title = anilist_info['title']['romaji']
                native_title = anilist_info['title'].get('native', 'N/A')
                is_adult = anilist_info['isAdult']
                episode = result.get('episode', 'N/A')
                similarity = result['similarity'] * 100
                from_time = result['from']
                to_time = result['to']
                video_url = result['video']
                image_url = result['image']

                result_embed = discord.Embed(title=f"{title} ({native_title})", color=config.PRIMARY_COLOR)
                result_embed.description = f"- Similarity: **`{similarity:.2f}%`**\n- Episode: **`{episode}`**\n- From: **`{from_time}`**\n- To: **`{to_time}`**\n- NSFW: **`{is_adult}`**"
                result_embed.set_image(url=image_url)

                if video_url:
                  await interaction.response.send_message(embed=result_embed, view=Video(video_url))
                else:
                  await interaction.response.send_message(embed=result_embed)
            else:
                await interaction.response.send_message(f"No matching anime found.", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to retrieve anime data. Please try again later.", ephemeral=True)

class Video(discord.ui.View):
    def __init__(self, video):
        super().__init__()
        url = video
        self.add_item(discord.ui.Button(label='Video URL', url=url))

async def setup(bot):
    await bot.add_cog(Anime(bot))

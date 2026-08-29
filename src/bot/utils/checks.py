import discord


async def is_bot_owner(
    interaction: discord.Interaction,
) -> bool:
    return await interaction.client.is_owner(
        interaction.user
    )
import discord

# hi, if you are editing this, just change the variables below

COLOR=0x131416 # this is the embed color

SUCCESS="<:success:1543115126675079229>"
ERROR="<:error:1543115139425771560>"
INFO="<:info:1543206967248556083>"
WARNING="<:warning:1543115144576372868>"
# ---- only till here ----

def success(message: str) -> discord.Embed:
    return discord.Embed(
    	color=COLOR,
        description=f"{SUCCESS}  {message}"
    )


def error(message: str) -> discord.Embed:
    return discord.Embed(
    	color=COLOR,
        description=f"{ERROR}  {message}"
    )


def info(message: str) -> discord.Embed:
    return discord.Embed(
    	color=COLOR,
        description=f"{INFO}  {message}"
    )


def warning(message: str) -> discord.Embed:
    return discord.Embed(
    	color=COLOR,
        description=f"{WARNING}  {message}"
    )
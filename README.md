# <img src="https://cdn.discordapp.com/emojis/1024629561360666676.webp?animated=true" width="28"> Tulip
This is the source code for a small Discord bot made with **discord.py** library, built for my Discord server - Velouré. It's still a little project, so expect things to change as I add more stuff. 🌷


## Features
Currently I've added,
- Logging: This sends all the logging messages printed on console directly to a Discord channel. Only bot owner can set it.
- Verification: This one's exclusive to my server so if you want to use it please update the role id, messages, etc yourself.
- Skullboard: Similar to starboard which you've often seen in servers.

## Things to note when self hosting
You can make changes to `./utils/embeds.py` and replace the emoji ids.

## Requirements

You'll need:

- Python 3.10+
- MySQL database (Create a free SQL database from [Aiven](https://aiven.io/))

## 🚀 Deploy to Render

The easiest way to get Tulip running is through Render.

<a href="https://render.com/deploy?repo=https://github.com/royalrizen/Tulip">
  <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render">
</a>

Clicking the button will create the Render service from the repository and take you through the environment variable setup.

Add the same variables from your `.env` to Render's **Environment Variables** section:

```env
DISCORD_TOKEN=
MYSQL_HOST=
MYSQL_PORT=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=
PREFIX=!
```

Render keeps these values separate from your source code, so you don't need to put secrets inside the repository. 🌱

**$Build Command** `pip install -e .` | **$Start Command** `tulip`

<br>

> [!NOTE]
> 1. You'll need a MySQL database that your Render service can connect to. Make sure the database allows connections from your Render service.
> 2. If you wish to keep the free tier active 24/7 then create a [cron job](https://cron-job.org/en/) and ping the web server's health endpoint. For example - `https://your-bot.onrender.com/health`

## 🏃 Running Tulip locally

Clone the repository:

```bash
git clone https://github.com/royalrizen/Tulip.git
cd Tulip
```

Locate the project folder, then install the package using:

```bash
pip install -e .
```

Rename the `.env.example` file to `.env` and add your credentials.

Then start the bot:

```bash
tulip
```

If everything is configured correctly, Tulip should log in and start loading its cogs.

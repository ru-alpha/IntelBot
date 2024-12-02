import discord
from discord.ext import commands
from datetime import datetime

# Replace with your bot token
BOT_TOKEN = "TOKEN"

# Replace with the ID of the relay channel for DMs
RELAY_CHANNEL_ID = 1311397018236747946  # Replace with the actual channel ID

# Replace with the ID of the channel for platform updates
PLATFORM_UPDATE_CHANNEL_ID = 1311397018236747946  # Replace with the actual channel ID

# Intents setup
intents = discord.Intents.all()

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# To store user platform presence
user_presence = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is online!")

    # Initialize user presence data
    for guild in bot.guilds:
        for member in guild.members:
            user_presence[member.id] = {
                "desktop": member.desktop_status,
                "web": member.web_status,
                "mobile": member.mobile_status,
            }

    # Send initial platform report
    await send_initial_status_report()


async def send_initial_status_report():
    """Send a message listing all users currently running web clients or notable combinations."""
    relay_channel = bot.get_channel(PLATFORM_UPDATE_CHANNEL_ID)
    if not relay_channel:
        print("Platform update channel not found. Please check the PLATFORM_UPDATE_CHANNEL_ID.")
        return

    notable_users = []
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            presence = user_presence.get(member.id, {})
            web_status = presence.get("web", discord.Status.offline)
            desktop_status = presence.get("desktop", discord.Status.offline)

            # Check for users who are active (online/idle/dnd) on web
            if web_status not in [discord.Status.offline, None]:
                status_emoji = {
                    discord.Status.online: "✅ Online",
                    discord.Status.idle: "🌙 Away",
                    discord.Status.dnd: "⛔ Do Not Disturb",
                }.get(web_status, "Unknown")
                notable_users.append(f"🌐 **{member.name}**: {status_emoji} on Web")

                # Special case: Online on web but idle on desktop
                if web_status == discord.Status.online and desktop_status == discord.Status.idle:
                    notable_users[-1] += " (Idle on Desktop)"

    if not notable_users:
        await relay_channel.send("No users are currently active on Web clients.")
        return

    # Split messages into chunks of <= 2000 characters
    message_chunks = []
    current_chunk = "**Initial Status Report:**\n"
    for user in notable_users:
        if len(current_chunk) + len(user) + 1 > 2000:  # +1 for newline
            message_chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += f"{user}\n"

    if current_chunk:
        message_chunks.append(current_chunk)

    # Send each chunk
    for chunk in message_chunks:
        await relay_channel.send(chunk)


@bot.event
async def on_presence_update(before, after):
    """Monitor platform presence changes and notify the relay channel."""
    relay_channel = bot.get_channel(PLATFORM_UPDATE_CHANNEL_ID)
    if not relay_channel:
        print("Platform update channel not found. Please check the PLATFORM_UPDATE_CHANNEL_ID.")
        return

    # Previous and current presence
    previous = user_presence.get(before.id, {})
    current = {
        "desktop": after.desktop_status,
        "web": after.web_status,
        "mobile": after.mobile_status,
    }

    # Update stored presence
    user_presence[after.id] = current

    # Detect changes for web client
    web_status_changed = previous.get("web") != current["web"]
    desktop_status_changed = previous.get("desktop") != current["desktop"]

    if web_status_changed or desktop_status_changed:
        # Detect if they are active (non-offline) on web and idle on desktop
        if current["web"] not in [discord.Status.offline, None]:
            status_emoji = {
                discord.Status.online: "✅ Online",
                discord.Status.idle: "🌙 Away",
                discord.Status.dnd: "⛔ Do Not Disturb",
            }.get(current["web"], "Unknown")
            if current["web"] == discord.Status.online and current["desktop"] == discord.Status.idle:
                await relay_channel.send(f"@everyone 🌐 **{after.name}** is {status_emoji} on Web and Idle on Desktop!")

            # Generic web client update
            embed = discord.Embed(
                title="Web Client Status Change",
                description=f"User: {after.name}",
                color=discord.Color.orange() if current["web"] == discord.Status.online else discord.Color.red()
            )
            embed.add_field(name="New Web Status", value=f"{status_emoji}", inline=False)
            embed.add_field(name="Desktop Status", value=f"{current['desktop']}", inline=True)
            embed.add_field(name="Mobile Status", value=f"{current['mobile']}", inline=True)
            embed.set_author(name=after.name, icon_url=after.avatar.url)
            embed.set_footer(text=f"Updated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            await relay_channel.send(embed=embed)


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author.bot:
        return

    # Relay DMs
    if isinstance(message.channel, discord.DMChannel):
        relay_channel = bot.get_channel(RELAY_CHANNEL_ID)
        if relay_channel is not None:
            embed = discord.Embed(
                description=message.content,
                color=discord.Color.blue()
            )
            embed.set_author(
                name=f"{message.author.name}",
                icon_url=message.author.avatar.url
            )
            embed.set_footer(
                text=f"Message to IntelBot at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
            await relay_channel.send(embed=embed)
        else:
            print("Relay channel not found. Please check the RELAY_CHANNEL_ID.")

    await bot.process_commands(message)


# Run the bot
bot.run(BOT_TOKEN)

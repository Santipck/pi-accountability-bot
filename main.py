import sys
sys.path.append("keepalive.py")
import nextcord
from nextcord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
from keepalive import keep_alive
import os
from dotenv import load_dotenv


keep_alive()

# Bot setup
intents = nextcord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
VERIFICATION_CHANNEL = "photo-verification"  # Replace with your channel name
LOGGING_CHANNEL = "punishment-incentive"  # Replace with your channel name
MEETING_INTERVAL_DAYS = 14  # Bi-weekly meetings

# Stores goal logs in memory (replace with a database for persistence)
goal_logs = {}

# Tracks which messages have been logged
logged_messages = set()  # Use message IDs to track completed logs

# Bot Events
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")


@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == "✅":
        guild = bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if channel.name == VERIFICATION_CHANNEL:
            # Check if the message is already logged
            if message.id in logged_messages:
                return  # Skip if already logged

            # Check if the reaction count meets the threshold
            for reaction in message.reactions:
                if reaction.emoji == "✅" and reaction.count >= 2:
                    user = message.author
                    log_channel = nextcord.utils.get(guild.text_channels, name=LOGGING_CHANNEL)
                    if not log_channel:
                        print("Logging channel not found!")
                        return

                    # Add the message to logged_messages
                    logged_messages.add(message.id)

                    # Log the goal
                    now = datetime.now()
                    log_entry = f"{user.mention} completed their goal on {now.strftime('%Y-%m-%d %H:%M:%S')}"

                    # Update goal_logs
                    if user.id not in goal_logs:
                        goal_logs[user.id] = {"logs": [], "count": 0}
                    goal_logs[user.id]["logs"].append(log_entry)
                    goal_logs[user.id]["count"] += 1

                    # Post in the logging channel
                    await log_channel.send(f"{log_entry} (Total completions: {goal_logs[user.id]['count']})")
                    return


# Command to view logs
@bot.command()
async def logs(ctx, member: nextcord.Member = None):
    if not member:
        member = ctx.author

    user_data = goal_logs.get(member.id)
    if not user_data:
        await ctx.send(f"📜 No logged goals found for {member.mention}.")
        return

    logs = user_data["logs"]
    count = user_data["count"]
    log_message = (
        f"📜 **Logs for {member.mention}:**\n"
        + "\n".join(logs)
        + f"\n\n**Total Completions:** {count}"
    )
    await ctx.send(log_message)

# Command to clear goal logs and logged messages
@bot.command()
@commands.has_permissions(administrator=True)  # Optional: Restrict this command to admins
async def reset(ctx):
    global goal_logs, logged_messages

    # Clear the dictionaries and sets
    goal_logs.clear()
    logged_messages.clear()

    await ctx.send("✅ All logged goals and messages have been reset. You can now retest.")

# Optional: Error handling for missing permissions
@reset.error
async def reset_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")


# Run the bot
load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))
import sys
import nextcord
from nextcord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import os
from dotenv import load_dotenv
import json 

#
import pandas as pd
import calmap
import io
import matplotlib.pyplot as plt 




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

# Stores goal logs in memory, replacing with database...
LOG_FILE = "goal_logs.json"
GOALS_FILE = "user_goals.json"
user_goals = {}  # Holds current goals

def save_user_goals():
    with open(GOALS_FILE, "w") as f:
        json.dump(user_goals, f)

def load_user_goals():
    global user_goals
    if os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, "r") as f:
            user_goals = json.load(f)


def load_goal_logs():
    global goal_logs
    try:
        with open(LOG_FILE, "r") as f:
            goal_logs = json.load(f)
            # Convert datetime strings if needed later
    except FileNotFoundError:
        goal_logs = {}


# Bot Events
@bot.event
async def on_ready():
    load_goal_logs()
    load_user_goals()
    print(f"Logged in as {bot.user}!")




# Setting Goals

@bot.command()
async def setgoal(ctx, *, goal_text: str):
    user_goals[str(ctx.author.id)] = goal_text
    save_user_goals()
    await ctx.send(f"✅ {ctx.author.mention}, your goal has been set to:\n> **{goal_text}**")

# Yours or others

@bot.command()
async def goal(ctx, member: nextcord.Member = None):
    member = member or ctx.author
    goal = user_goals.get(str(member.id))
    if goal:
        await ctx.send(f"🎯 **{member.display_name}'s goal:**\n> {goal}")
    else:
        await ctx.send(f"⚠️ WARNING {member.display_name} has not set a goal yet. :O")



def save_goal_logs():
    with open(LOG_FILE, "w") as f:
        json.dump(goal_logs, f)

# Tracks which messages have been logged
logged_messages = set()  # Use message IDs to track completed logs

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

                    save_goal_logs()

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

    timestamps = []
    for entry in logs:
        try:
            time_str = entry.split("on ")[1]
            timestamps.append(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S"))
        except Exception:
            continue

        streak = calculate_streak(timestamps)

    heatmap_image = generate_heatmap_image(timestamps)

    if heatmap_image:
        file = nextcord.File(heatmap_image, filename="heatmap.png")
        await ctx.send(
            content=f"🔥 **{member.display_name}'s current streak: {streak} day(s)**\n📜 **Total Completions:** {count}",
            file=file
        )
    else:
        await ctx.send(f"📜 Logs for {member.mention}, but no valid timestamps found.")


# HEAT

def generate_heatmap_image(timestamps):
    if not timestamps:
        return None

    # Set default font
    plt.rcParams['font.family'] = 'DejaVu Sans'

    # Create a Series
    date_series = pd.Series(1, index=pd.to_datetime(timestamps))

    fig, ax = calmap.calendarplot(
        date_series,
        cmap='Greens',
        fillcolor='lightgray',
        linewidth=0.5,
        fig_kws=dict(figsize=(16, 4))
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def calculate_streak(timestamps):
    if not timestamps:
        return 0
    
    # Just date
    dates = sorted(set(ts.date() for ts in timestamps), reverse =True)
    today = datetime.now().date()
    streak = 0

    for i, day in enumerate(dates):
        expected_day = today - timedelta(days=i)
        if day == expected_day:
            streak += 1
        else:
            break
    
    return streak

@bot.command(hidden=True)
async def cayden(ctx): #timeless classic
    await ctx.send("https://cdn.discordapp.com/attachments/1278741106309468242/1372644177065676911/rr.mp4?ex=68278602&is=68263482&hm=a39ab968204763c86fdd8c67e6e359d41dfb5fca983c83e7ee80dd5be704ab22&")

# find better way to !log 

# heatmap/autologging visually

# streaking

# punishment/incentive timer

# help command (lolz)

# brain damage simulator

# Run the bot
load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))
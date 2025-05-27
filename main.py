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
import matplotlib.colors as mcolors




# Bot setup
intents = nextcord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True  
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
VERIFICATION_CHANNEL = "photo-verification"  # Replace with given channel name for verifying goals
LOGGING_CHANNEL = "punishment-incentive"  #  Replace with given channel name for confirming logs (placehold)
MEETING_INTERVAL_DAYS = 14  # Bi-weekly meetings


# Data Mngmnt
LOG_FILE = "goal_logs.json"
GOALS_FILE = "user_goals.json"
user_goals = {}  # Holds current goals
CYCLE_FILE = "cycle_data.json"
PARTNERS_FILE = "partners.json"
partners = {} 

def save_user_goals():
    with open(GOALS_FILE, "w") as f:
        json.dump({str(k): v for k, v in user_goals.items()}, f)

def load_user_goals():
    global user_goals
    if os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, "r") as f:
            user_goals = {int(k): v for k, v in json.load(f).items()}


def load_goal_logs():
    global goal_logs
    try:
        with open(LOG_FILE, "r") as f:
            goal_logs = {int(k): v for k, v in json.load(f).items()}
    except FileNotFoundError:
        goal_logs = {}


 # Looooad/save cycle data
def load_cycle_data():
    try:
        with open(CYCLE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
# Progression (cycle)

@bot.command()
@commands.has_permissions(administrator=True)
async def startcycle(ctx):
    data = load_cycle_data()

    if data:
        await ctx.send("⚠️ A cycle is already active. Use `!cyclestatus` to view it.")
        return

    # Create a 4-week cycle starting today
    start_date = datetime.now()
    end_date = start_date + timedelta(weeks=4)

    check_ins = [
        (start_date + timedelta(weeks=i)).strftime("%Y-%m-%d")
        for i in range(4)
    ]

    cycle_data = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "check_ins": check_ins,
        "participants": []
    }

    save_cycle_data(cycle_data)
    await ctx.send(
        f"✅ A new 4-week cycle has started!\n"
        f"📅 Start: `{cycle_data['start_date']}`\n"
        f"📅 End: `{cycle_data['end_date']}`\n"
        f"🔁 Use `!joincycle` to participate."
    )

@bot.command()
async def cyclestatus(ctx):
    data = load_cycle_data()
    if not data:
        await ctx.send("❌ No cycle is currently active.")
        return

    start = datetime.strptime(data["start_date"], "%Y-%m-%d")
    end = datetime.strptime(data["end_date"], "%Y-%m-%d")
    today = datetime.now()

    days_remaining = (end - today).days
    current_week = ((today - start).days // 7) + 1
    current_week = min(current_week, 4)

    next_check_in = "-_- All done!" if days_remaining <= 0 else data["check_ins"][current_week - 1]

    await ctx.send(
        f"📊 **Cycle Status**\n"
        f"🗓️ Week: {current_week} of 4\n"
        f"📅 Days Remaining: {max(0, days_remaining)}\n"
        f"🛎️ Next Check-In: `{next_check_in}`"
    )


# Daily background task for reminders
@tasks.loop(hours=24)
async def daily_cycle_check():
    data = load_cycle_data()
    if not data:
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    last_sent = data.get("last_check_in_sent")

    if today_str in data["check_ins"] and last_sent != today_str:
        channel = nextcord.utils.get(bot.get_all_channels(), name="general") # Change with a dedicated check in channel???
        if channel:
            await channel.send(
                f"📣 **WEEKLY CHECK-IN REMINDER"
            )
        data["last_check_in_sent"] = today_str
        save_cycle_data(data)

def save_cycle_data(data):
    with open(CYCLE_FILE, "w") as f:
        json.dump(data, f)

@bot.command()
async def joincycle(ctx):
    user_id = ctx.author.id
    data = load_cycle_data()

    if not data:
        await ctx.send("❌ No active cycle to join.")
        return

    participants = data.get("participants", [])
    if user_id in participants:
        await ctx.send(f"🔁 {ctx.author.display_name}, you're already in this cycle!")
        return

    participants.append(user_id)
    data["participants"] = participants
    save_cycle_data(data)

    await ctx.send(f"✅ {ctx.author.display_name}, you've joined the current cycle! Let's go 💪")

@bot.command()
@commands.has_permissions(administrator=True)
async def endcycle(ctx):
    data = load_cycle_data()

    if not data:
        await ctx.send("❌ No active cycle to end.")
        return

    # Wipe cycle data
    with open(CYCLE_FILE, "w") as f:
        json.dump({}, f)

    await ctx.send("🔚 The current cycle has been forcefully ended by an admin.")


# Bot Events
@bot.event
async def on_ready():
    load_goal_logs()
    load_user_goals()
    load_partners()
    daily_cycle_check.start()
    print(f"Logged in as {bot.user}! Goal logs and cycle check loaded!")




# Setting Goals

@bot.command()
async def setgoal(ctx, *, goal_text: str):
    user_goals[str(ctx.author.id)] = goal_text
    save_user_goals()
    await ctx.send(f"✅ {ctx.author.mention}, your goal has been set to:\n> **{goal_text}**")

# partner-goal 

def load_partners():
    global partners
    if os.path.exists(PARTNERS_FILE):
        with open(PARTNERS_FILE, "r") as f:
            partners = {int(k): int(v) for k, v in json.load(f).items()}

def save_partners():
    with open(PARTNERS_FILE, "w") as f:
        json.dump({str(k): str(v) for k, v in partners.items()}, f)

@bot.command()
async def setpartner(ctx, member: nextcord.Member):
    user_id = str(ctx.author.id)
    partner_id = str(member.id)

    if user_id == partner_id:
        await ctx.send(">:( You can't partner with yourself...")
        return

    # Mutual binding
    partners[user_id] = partner_id
    partners[partner_id] = user_id
    save_partners()

    await ctx.send(f"🤝 {ctx.author.display_name} is now partnered with {member.display_name}!")

# Partner Status Commanding

@bot.command()
async def partner(ctx):
    partner_id = partners.get(str(ctx.author.id))
    if not partner_id:
        await ctx.send(" >:( You haven't set a partner yet. Use `!setpartner @user`.")
        return

    partner_user = ctx.guild.get_member(int(partner_id))
    if partner_user:
        await ctx.send(f"🤝 Your partner is **{partner_user.display_name}**.")
    else:
        await ctx.send("⚠️ Your partner may have left the server...")


@bot.command()
async def partnergoal(ctx):
    partner_id = partners.get(str(ctx.author.id))
    if not partner_id:
        await ctx.send("❌ You don't have a partner set.")
        return

    partner_goal = user_goals.get(partner_id)
    if partner_goal:
        partner_user = ctx.guild.get_member(int(partner_id))
        name = partner_user.display_name if partner_user else "Your Partner"
        await ctx.send(f"🎯 **{name}'s goal:**\n> {partner_goal}")
    else:
        await ctx.send(" >:( Your partner hasn't set a goal yet.")


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
        json.dump({str(k): v for k, v in goal_logs.items()}, f)

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

    plt.rcParams['font.family'] = 'DejaVu Sans'

    # Convert timestamps into a Pandas Series
    date_series = pd.Series([1] * len(timestamps), index=pd.to_datetime([ts.date() for ts in timestamps]))
    date_series = date_series.groupby(level=0).sum()  # Aggregate completions per day

    # Create a custom colormap with a gradient from light to dark green
    cmap = mcolors.LinearSegmentedColormap.from_list("custom_green", ["#e0f2e0", "#b0c475"], N=256)

    fig, ax = calmap.calendarplot(
        date_series,
        cmap=cmap,
        fillcolor="#444444",
        linewidth=0.5,
        fig_kws=dict(figsize=(16, 4)),
        vmin=0,
        vmax=max(1, date_series.max())
    )

    # Set background colors
    fig.patch.set_facecolor("#333333")
    if isinstance(ax, dict):
        for a in ax.values():
            a.set_facecolor("#333333")
    else:
        for a in ax.flat:
            a.set_facecolor("#333333")

    # Save to buffer
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

# leaderboard idea

@bot.command()
async def leaderboard(ctx, top_n: int = 5):
    if not goal_logs:
        await ctx.send(" >:( No goal completions logged yet!")
        return

    sorted_users = sorted(goal_logs.items(), key=lambda x: x[1]["count"], reverse=True)
    message = "🧠💪 **Top Goal Completers** 💪🧠 \n"

    for i, (user_id, data) in enumerate(sorted_users[:top_n], start=1):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else f"<@{user_id}>"
        message += f"**#{i}** - {name} → {data['count']} completions\n"

    await ctx.send(message)

# error handling

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"❌ Error: {str(error)}")

# Help command
bot.remove_command("help")

@bot.command()
async def help(ctx):
    help_text = (
        "**📘 Commands Help**\n"
        "🎯 `!setgoal [goal]` - Set your current goal.\n"
        "👥 `!setpartner @user` - Set your accountability partner.\n"
        "🧾 `!goal` - View your goal.\n"
        "🎯 `!partnergoal` - View your partner's goal.\n"
        "📜 `!logs` - View your log + streak.\n"
        "🏆 `!leaderboard` - Show top goal completions.\n"
        "📅 `!cyclestatus` - Check the current cycle progress.\n"
        "❓ `!help` - View this help message."
    )
    await ctx.send(help_text)

@bot.command(hidden=True)
async def cayden(ctx): #timeless classic
    await ctx.send("https://cdn.discordapp.com/attachments/1278741106309468242/1372644177065676911/rr.mp4?ex=68278602&is=68263482&hm=a39ab968204763c86fdd8c67e6e359d41dfb5fca983c83e7ee80dd5be704ab22&")

# find better way to !log 

### Cool/useful emojis copypasta ✅🤝📅📊🔥🎯📈💬🛎️🔁📜🧠💪📌⏳👥👣📝🧾⚠️🔐👀🧪

# heatmap/autologging visually

# streaking

# punishment/incentive timer

# help command (lolz)

# brain damage simulator

# Run the bot
load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))
# bot.py
import os
import re
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from collections import deque, defaultdict
from threading import Thread

import nextcord
from nextcord.ext import commands
from flask import Flask

# -----------------------
# CONFIG
# -----------------------
TOKEN = os.environ.get("TOKEN")
PORT = int(os.environ.get("PORT", 5000))

# Immune role
IMMUNE_ROLE_ID = 1436371868507439205

# Bardock image URL
BARD0CK_ICON = "https://cdn.discordapp.com/attachments/1371058100462948438/1446739720456634368/EjodqurX0AYCUP-.jpg?ex=693514dc&is=6933c35c&hm=b704945cd6fe32c50ddcf3d7be68d50e58ad709a120e8253088128929f8c6e9b&"

# Anti settings
EMOJI_THRESHOLD = 5
SPAM_MSG_THRESHOLD = 5
SPAM_WINDOW_SECONDS = 10
LONGTEXT_THRESHOLD = 500

TIMEOUT_SECONDS_FOR_SPAM = 60 * 5
TIMEOUT_SECONDS_FOR_LONGTEXT = 60 * 10
TIMEOUT_SECONDS_FOR_EMOJI = 60 * 2
TIMEOUT_SECONDS_FOR_LINK = 60 * 5

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("BardockGuardian")

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

user_message_times = defaultdict(lambda: deque(maxlen=100))

# Regex
URL_REGEX = re.compile(r"(https?://[^\s]+)|(www\.[^\s]+)", re.IGNORECASE)
CUSTOM_EMOJI_REGEX = re.compile(r"<a?:\w+:\d+>")
UNICODE_EMOJI_REGEX = re.compile(
    "[" 
    "\U0001F300-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U0001F1E6-\U0001F1FF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]"
)


def count_emojis(text: str) -> int:
    return len(CUSTOM_EMOJI_REGEX.findall(text)) + len(UNICODE_EMOJI_REGEX.findall(text))


def has_non_tenor_link(text: str):
    for match in URL_REGEX.finditer(text):
        url = match.group(0).lower()
        if "tenor.com" in url or "tenor.googleapis.com" in url:
            continue
        return True, match.group(0)
    return False, ""


async def majestic_dm(member, reason, details=""):
    """Bardock DM message"""
    msg = (
        f"**Oi, {member.display_name}. Bardock speaking.**\n\n"
        f"{reason}\n\n"
        f"{details}\n\n"
        "You're stronger than this. Fight with control — not chaos. ⚔️🔥"
    )

    try:
        await member.send(msg)
    except:
        log.warning(f"Couldn't DM {member}")


async def apply_timeout(guild, member, seconds, reason):
    try:
        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        await member.edit(communication_disabled_until=until, reason=reason)
    except Exception as e:
        log.exception(f"Timeout failed for {member}: {e}")


def is_immune(member):
    try:
        if member.guild_permissions.administrator:
            return True
        for r in member.roles:
            if r.id == IMMUNE_ROLE_ID:
                return True
    except:
        pass
    return False


# -----------------------
# EVENTS
# -----------------------
@bot.event
async def on_ready():
    log.info(f"Bardock Bot Online — {bot.user}")


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot or message.guild is None:
        return

    member = message.author
    guild = message.guild
    content = message.content or ""

    if is_immune(member):
        return

    # -----------------------
    # Anti-longtext
    # -----------------------
    if len(content) >= LONGTEXT_THRESHOLD:
        try: await message.delete()
        except: pass

        await apply_timeout(guild, member, TIMEOUT_SECONDS_FOR_LONGTEXT, "Longtext rule")

        await majestic_dm(
            member,
            "You're dropping massive walls of text in the middle of a battlefield.",
            f"Your message had **{len(content)} characters**, allowed max is **{LONGTEXT_THRESHOLD}**."
        )
        return

    # -----------------------
    # Anti-emoji spam
    # -----------------------
    emoji_count = count_emojis(content)
    if emoji_count >= EMOJI_THRESHOLD:
        try: await message.delete()
        except: pass

        await apply_timeout(guild, member, TIMEOUT_SECONDS_FOR_EMOJI, "Emoji spam")

        await majestic_dm(
            member,
            "That message was nothing but emoji noise.",
            f"Detected **{emoji_count} emojis** (limit is {EMOJI_THRESHOLD})."
        )
        return

    # -----------------------
    # Anti-links
    # -----------------------
    has_bad, bad_link = has_non_tenor_link(content)
    if has_bad:
        try: await message.delete()
        except: pass

        await apply_timeout(guild, member, TIMEOUT_SECONDS_FOR_LINK, "Illegal link")

        await majestic_dm(
            member,
            "You posted a link that doesn't belong in this server.",
            f"**{bad_link}** is blocked. Only **Tenor** links are allowed."
        )
        return

    # -----------------------
    # Anti-spam
    # -----------------------
    now = datetime.now().timestamp()
    times = user_message_times[(guild.id, member.id)]
    times.append(now)

    while times and now - times[0] > SPAM_WINDOW_SECONDS:
        times.popleft()

    if len(times) >= SPAM_MSG_THRESHOLD:
        # Delete recent messages
        try:
            def check(m):
                return (
                    m.author.id == member.id and
                    datetime.now().timestamp() - m.created_at.replace(tzinfo=timezone.utc).timestamp() <= SPAM_WINDOW_SECONDS
                )
            await message.channel.purge(limit=50, check=check)
        except:
            pass

        await apply_timeout(guild, member, TIMEOUT_SECONDS_FOR_SPAM, "Spam")

        embed = nextcord.Embed(
            title="⚔️ Bardock's Warning",
            description=(
                f"{member.mention}, you're firing off messages like you're losing control.\n"
                f"I counted **{len(times)} messages in {SPAM_WINDOW_SECONDS} seconds**."
            ),
            color=0xFF4500
        )
        embed.add_field(
            name="Punishment",
            value=f"🔇 Timeout: **{TIMEOUT_SECONDS_FOR_SPAM // 60} minutes**"
        )
        embed.set_author(name="Bardock", icon_url=BARD0CK_ICON)

        try:
            await message.channel.send(embed=embed)
        except:
            pass

        await majestic_dm(
            member,
            "You're spamming like you're panicking in combat.",
            f"Sent **{len(times)} messages** in {SPAM_WINDOW_SECONDS}s. Timeout applied."
        )

        user_message_times[(guild.id, member.id)].clear()
        return


# -----------------------
# COMMANDS
# -----------------------
@bot.command()
async def ping(ctx):
    await ctx.reply("Bardock reporting — I'm online. ⚔️🔥")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: nextcord.Member):
    try:
        await member.edit(communication_disabled_until=None)
        await ctx.send(f"{member.mention} has been released.")
    except:
        await ctx.send("Couldn't untimeout.")


# -----------------------
# FLASK SERVER
# -----------------------
app = Flask("bardock-bot")

@app.route("/")
def index():
    return "Bardock Guardian Bot Running", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# -----------------------
# MAIN
# -----------------------
def main():
    if TOKEN is None:
        log.error("TOKEN missing.")
        return

    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    bot.run(TOKEN)

if __name__ == "__main__":
    main()

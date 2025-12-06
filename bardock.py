# bot.py
import os
import asyncio
import nextcord
from nextcord.ext import commands
from flask import Flask
import threading
import re
import time

# -----------------------------
# CONFIG
# -----------------------------
TOKEN = os.getenv("TOKEN")
INTENTS = nextcord.Intents.all()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)

IMMUNE_ROLE = 1436371868507439205
IMMUNE_USER = 1338875321545392152  # immune owner

EMOJI_REGEX = re.compile(r"[\U0001F300-\U0001FAFF]")
LINK_REGEX = re.compile(r"https?://[^\s]+")

SPAM_TRACKER = {}  # {user_id: [timestamps]}

# -----------------------------
# HELPER — CHECK IMMUNITY
# -----------------------------
def is_immune(member):
    if member.id == IMMUNE_USER:
        return True
    if any(role.id == IMMUNE_ROLE for role in member.roles):
        return True
    return False

# -----------------------------
# BARDock DM Messages
# -----------------------------
def bardock_msg(reason):
    return (
        f"**Warrior… Bardock speaks.**\n"
        f"You walk a path that invites chaos — and I don’t tolerate that.\n\n"
        f"**Your mistake:** {reason}\n\n"
        f"Stand firm, correct yourself, and don’t force my hand again.\n"
        f"**A Saiyan rises through discipline — not recklessness.**"
    )

# -----------------------------
# EVENT LISTENER
# -----------------------------
@BOT.event
async def on_ready():
    print(f"⚔️ BardockBot online as {BOT.user}")

@BOT.event
async def on_message(message):
    if message.author.bot:
        return

    author = message.author
    content = message.content or ""

    # --------------------------
    # IMMUNITY CHECK
    # --------------------------
    if is_immune(author):
        await BOT.process_commands(message)
        return

    # --------------------------
    # ANTI-EMOJI SPAM
    # --------------------------
    emoji_count = len(EMOJI_REGEX.findall(content))
    if emoji_count >= 5:
        try:
            await message.delete()
            await author.send(bardock_msg("Excessive emoji usage."))
        except:
            pass

    # --------------------------
    # ANTI-LINK (except tenor)
    # --------------------------
    links = LINK_REGEX.findall(content)
    for link in links:
        if "tenor.com" not in link:
            try:
                await message.delete()
                await author.send(bardock_msg("Unauthorized link detected."))
            except:
                pass
            break  # delete once per message

    # --------------------------
    # ANTI-LONGTEXT
    # --------------------------
    if len(content) >= 500:
        try:
            await message.delete()
            await author.timeout(nextcord.utils.utcnow() + nextcord.utils.timedelta(seconds=30))
            await author.send(bardock_msg("Message too long — over 500 characters."))
        except:
            pass

    # --------------------------
    # ANTI-SPAM (5+ messages/10s)
    # --------------------------
    now = time.time()
    if author.id not in SPAM_TRACKER:
        SPAM_TRACKER[author.id] = []

    SPAM_TRACKER[author.id] = [t for t in SPAM_TRACKER[author.id] if now - t <= 10]
    SPAM_TRACKER[author.id].append(now)

    if len(SPAM_TRACKER[author.id]) >= 5:
        try:
            await author.timeout(nextcord.utils.utcnow() + nextcord.utils.timedelta(seconds=30))
            await author.send(bardock_msg("Rapid-fire messaging detected — calm your battle spirit."))
        except:
            pass
        SPAM_TRACKER[author.id] = []

    await BOT.process_commands(message)

# -----------------------------
# FLASK KEEP-ALIVE FOR RENDER
# -----------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "BardockBot Running."

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run_flask).start()

# -----------------------------
# RUN BOT
# -----------------------------
if TOKEN is None:
    raise Exception("TOKEN environment variable missing!")

BOT.run(TOKEN)

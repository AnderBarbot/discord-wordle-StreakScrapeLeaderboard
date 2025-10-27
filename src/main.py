import os
import logging
from dotenv import load_dotenv

import discord
from discord.ext import commands

from storage import init_db, load_all_users, clear_all_users
from processes import parse_wordle_message, build_leaderboard_embed

# --- Setup ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wordle_bot")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=None, intents=intents)
bot.user_dict = {}
bot.processed_message_ids = set()

# --- Events ---
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    init_db()
    bot.user_dict.update(load_all_users())
    logger.info(f"Loaded {len(bot.user_dict)} users from DB.")

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        logger.warning(f"Failed to sync slash commands: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if "Your group is on" not in message.content:
        return
    try:
        logger.debug(f"Parsing attempt: content={message.content.replace("\n", " ")}")
        parsed = await parse_wordle_message(message, bot.user_dict)
        if parsed:
            logger.info(f"Parsed Wordle results from message {message.id}")
        else:
            logger.debug(f"Message {message.id} parsed but returned no result")
    except Exception:
        logger.exception("Error parsing message")

# --- Slash Commands ---
@bot.tree.command(name="leaderboard", description="Show Wordle leaderboard")
async def leaderboard(interaction: discord.Interaction):
    embed = build_leaderboard_embed(bot.user_dict)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="catchup", description="Parse all past Wordle messages in this channel")
async def catchup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    count = 0
    async for msg in interaction.channel.history(limit=None, oldest_first=True):
        if "Your group is on" not in msg.content:
            continue
        if msg.author == bot.user or msg.id in bot.processed_message_ids:
            continue
        try:
            logger.debug(f"Parsing attempt: content={msg.content.replace("\n", " ")}")
            parsed = await parse_wordle_message(msg, bot.user_dict)
            if parsed:
                bot.processed_message_ids.add(msg.id)
                count += 1
        except Exception:
            logger.exception(f"Error parsing message {msg.id}")
    await interaction.followup.send(f"✅ Catch-up complete. Parsed {count} messages.", ephemeral=True)

@bot.tree.command(name="reset", description="Reset all Wordle data (admin only)")
async def reset(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
        return
    clear_all_users()
    bot.user_dict.clear()
    await interaction.response.send_message("🗑️ All data has been reset.", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)

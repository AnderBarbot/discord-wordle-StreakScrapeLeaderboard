import os
import logging
from dotenv import load_dotenv
import discord
from discord.ext import commands

"""
main.py
---------
Entry point for the Wordle Discord Bot.
Initializes the bot, registers slash commands,
handles events (message parsing, catch-up, reset),
and coordinates between the database and parsing modules.
"""

from storage import (
    init_db, load_all_users, clear_all_users,
    message_already_processed, mark_message_processed
)
from processes import parse_wordle_message, build_leaderboard_embed, GROUP_TRIGGER

# --- Setup ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wordle_bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  
bot = commands.Bot(command_prefix=None, intents=intents)

bot.user_dict = {}

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
    if GROUP_TRIGGER not in message.content:
        return
    if message_already_processed(message.id):
        return

    try:
        parsed = await parse_wordle_message(message, bot.user_dict)
        if parsed:
            mark_message_processed(message.id)
            logger.info(f"[Parse] Added {parsed} results from message {message.id}")

                        # --- NEW CODE START ---
            try:
                embed = await build_leaderboard_embed(bot.user_dict, message.guild)
                channel = message.channel
                await channel.send(embed=embed)
                logger.info(f"[Leaderboard] Updated leaderboard sent to #{channel.name}")
            except Exception:
                logger.exception("Error sending updated leaderboard")
    except Exception:
        logger.exception("Error parsing message")

# --- Slash Commands ---
@bot.tree.command(name="leaderboard", description="Show Wordle leaderboard")
async def leaderboard(interaction: discord.Interaction):
    embed = await build_leaderboard_embed(bot.user_dict, interaction.guild)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="catchup", description="Parse all past Wordle messages in this channel")
async def catchup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    count = 0
    async for msg in interaction.channel.history(limit=None, oldest_first=True):
        if GROUP_TRIGGER not in msg.content or msg.author == bot.user:
            continue
        if message_already_processed(msg.id):
            logger.debug(f"message already processed: {msg.id}")
            continue
        try:
            logger.debug(f"parsing message {msg.content}")
            parsed = await parse_wordle_message(msg, bot.user_dict)
            if parsed:
                mark_message_processed(msg.id)
                count += parsed
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

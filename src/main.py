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
from processes import handle_all_messages, build_leaderboard_embed, set_handicap, set_user_lowest_score

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

    parsed = await handle_all_messages(message, bot.user_dict)
    if parsed:
        try:
            embed = await build_leaderboard_embed(bot.user_dict, message.guild)
            await message.channel.send(embed=embed)
            logger.info(f"[Leaderboard] Updated after processing message {message.id}")
        except Exception:
            logger.exception("Error sending updated leaderboard")

# --- Slash Commands ---
@bot.tree.command(name="leaderboard", description="Show Wordle leaderboard")
async def leaderboard(interaction: discord.Interaction):
    embed = await build_leaderboard_embed(bot.user_dict, interaction.guild)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="catchup", description="Parse all past Wordle and cheater messages in this channel")
async def catchup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    count = 0
    async for msg in interaction.channel.history(limit=None, oldest_first=True):
        if msg.author == bot.user:
            continue
        parsed = await handle_all_messages(msg, bot.user_dict)
        if parsed:
            count += parsed
    await interaction.followup.send(f"✅ Catch-up complete. Parsed {count} messages.", ephemeral=True)

@bot.tree.command(name="reset", description="Reset all Wordle data (admin only)")
async def reset(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
        return
    clear_all_users()
    bot.user_dict.clear()
    await interaction.response.send_message("🗑️ All data has been reset.", ephemeral=True)

@bot.tree.command(name="handicap", description="Set handicap value for a user (decimal, non-integer)")
@discord.app_commands.describe(user="User to handicap", value="Handicap value (decimal, non-integer)")
async def handicap(interaction: discord.Interaction, user: discord.Member, value: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only admins can set handicaps.", ephemeral=True)
        return
    try:
        val = float(value)
        if val == int(val):
            await interaction.response.send_message("❌ Handicap value cannot be an integer. Please provide a decimal with up to 2 decimals.", ephemeral=True)
            return
        val = round(val, 2)
    except ValueError:
        await interaction.response.send_message("❌ Invalid handicap value. Please provide a decimal number.", ephemeral=True)
        return
    
    result = await set_handicap(str(user.id), val, bot.user_dict)
    if result:
        await interaction.response.send_message(f"✅ Handicap set for {user.display_name} to {val}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Failed to set handicap. User not found.", ephemeral=True)

@bot.tree.command(name="cheater", description="Set a user's lowest score to a specified value (admin only)")
@discord.app_commands.describe(user="User whose lowest score to replace", score="New score to set (integer)")
async def cheater(interaction: discord.Interaction, user: discord.Member, score: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
        return
    if score < 1 or score > 10:
        await interaction.response.send_message("❌ Score must be an integer between 1 and 10.", ephemeral=True)
        return

    result = await set_user_lowest_score(str(user.id), score, bot.user_dict)
    if result:
        await interaction.response.send_message(f"✅ Replaced {user.display_name}'s lowest score with {score}.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Failed to update score. User not found or no scores recorded.", ephemeral=True)



if __name__ == "__main__":
    bot.run(TOKEN)
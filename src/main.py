#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# main.py — Wordle Bot Entrypoint
# Now using slash commands and dual leaderboards

import os
import logging
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio

from storage import init_db, load_all_users, save_user
from processes import parse_wordle_message

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ---- Logging setup ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---- Discord setup ----
intents = discord.Intents.default()  # No privileged intents needed
bot = commands.Bot(command_prefix="!", intents=intents)
user_dict = {}

# ---- Ready event ----
@bot.event
async def on_ready():
    logger.info("✅ Logged in as %s (ID: %s)", bot.user, bot.user.id)
    await init_db()

    global user_dict
    user_dict.update(await load_all_users())

    try:
        synced = await bot.tree.sync()
        logger.info("✅ Synced %d slash commands", len(synced))
    except Exception as e:
        logger.error("Failed to sync commands: %s", e)


# ---- Wordle message listener ----
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    result = await parse_wordle_message(message, user_dict)
    if result:
        await save_user(result)
        logger.info("Saved result for %s", result.display_name)

    # Slash commands coexist with prefix, but we don’t need both now
    await bot.process_commands(message)


# ---- Slash commands ----
@bot.tree.command(name="leaderboard", description="Show the all-time leaderboard")
async def leaderboard(interaction: discord.Interaction):
    from processes import build_leaderboard_embed
    embed = build_leaderboard_embed(user_dict, mode="global")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="streakleaderboard", description="Show the current streak leaderboard")
async def streak_leaderboard(interaction: discord.Interaction):
    from processes import build_leaderboard_embed
    embed = build_leaderboard_embed(user_dict, mode="streak")
    await interaction.response.send_message(embed=embed)


# ---- Main entrypoint ----
if __name__ == "__main__":
    logger.info("Starting Wordle Bot with slash commands...")
    bot.run(TOKEN)

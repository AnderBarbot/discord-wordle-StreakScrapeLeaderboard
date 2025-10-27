#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# processes.py — Wordle Bot logic, leaderboard computation, parsing, and stats.

import asyncio
import math
import re
import statistics
from datetime import datetime
from typing import Dict, List

import discord
from User import User
from WordleResult import WordleResult


# ---------- CONFIGURATION ----------
WORDLE_REGEX = re.compile(r"Wordle (\d+) ([1-6X])/6(?:\*?)", re.IGNORECASE)
BAYESIAN_THRESHOLD = 10  # n₀ (minimum games for Bayesian averaging)


# ---------- CORE FUNCTIONS ----------

async def parse_result(message: discord.Message, user_dict: Dict[int, User]):
    """
    Parse a Wordle result from a user's message and update stats.
    """
    match = WORDLE_REGEX.search(message.content)
    if not match:
        return  # Not a valid Wordle message

    wordle_num = int(match.group(1))
    tries_str = match.group(2)
    hard_mode = "*" in message.content

    tries = 7 if "X" in tries_str else int(tries_str)  # 'X' treated as fail (7)

    user_id = message.author.id
    if user_id not in user_dict:
        user_dict[user_id] = User(message.author)

    user = user_dict[user_id]

    # Avoid duplicates
    if wordle_num in user.played_nums:
        return

    result = WordleResult(
        number=wordle_num,
        tries=tries,
        hard=hard_mode,
        post_time=message.created_at,
        grid=[],
    )

    user.results.append(result)
    user.played_nums.append(wordle_num)
    user.total_games += 1
    await asyncio.sleep(0)  # Yield for async fairness


async def catchup(channel: discord.TextChannel, user_dict: Dict[int, User]):
    """
    Parses message history to populate stats initially.
    """
    async for message in channel.history(limit=None, oldest_first=True):
        await parse_result(message, user_dict)


# ---------- STATISTICS HELPERS ----------

def _bayesian_average(mean, n, global_mean, threshold=BAYESIAN_THRESHOLD):
    """Compute Bayesian average for ranking stability."""
    return (threshold * global_mean + n * mean) / (threshold + n)


def _user_stats(user: User):
    """Compute all user-level statistics."""
    if not user.results:
        return None

    valid_results = [r for r in user.results if r.tries <= 6]
    failed = [r for r in user.results if r.tries == 7]

    if not valid_results:
        return None

    tries_list = [r.tries for r in valid_results]
    avg = sum(tries_list) / len(tries_list)
    stddev = statistics.pstdev(tries_list) if len(tries_list) > 1 else 0.0

    # Compute streak info
    sorted_results = sorted(user.results, key=lambda r: r.number)
    current_streak = 0
    longest_streak = 0
    streak_tries = []

    prev_num = None
    for r in sorted_results:
        if r.tries == 7:
            current_streak = 0
            streak_tries = []
            continue
        if prev_num is None or r.number == prev_num + 1:
            current_streak += 1
            streak_tries.append(r.tries)
        else:
            longest_streak = max(longest_streak, current_streak)
            current_streak = 1
            streak_tries = [r.tries]
        prev_num = r.number

    longest_streak = max(longest_streak, current_streak)
    streak_avg = (sum(streak_tries) / len(streak_tries)) if streak_tries else 0.0
    completion = len(valid_results) / (len(valid_results) + len(failed)) * 100

    return {
        "name": user.author.display_name,
        "avg": avg,
        "stddev": stddev,
        "current_streak": current_streak,
        "streak_avg": streak_avg,
        "longest_streak": longest_streak,
        "completion": completion,
        "games_played": len(user.results),
    }


# ---------- LEADERBOARD GENERATION ----------

async def compute_leaderboards(user_dict: Dict[int, User], show="overall"):
    """
    Compute and return a Discord Embed containing the leaderboard.
    show = "overall" | "streaks"
    """

    stats = [_user_stats(u) for u in user_dict.values()]
    stats = [s for s in stats if s is not None]

    if not stats:
        embed = discord.Embed(
            title="No data yet!",
            description="No Wordle results have been recorded.",
            color=discord.Color.orange(),
        )
        return embed

    global_mean = sum(s["avg"] for s in stats) / len(stats)

    # Apply Bayesian ranking
    for s in stats:
        s["bayes"] = _bayesian_average(s["avg"], s["games_played"], global_mean)

    # Filter according to leaderboard type
    if show == "overall":
        filtered = [s for s in stats if s["games_played"] >= BAYESIAN_THRESHOLD]
        title = "🏆 Wordle Leaderboard (Overall)"
        desc = f"Players with ≥{BAYESIAN_THRESHOLD} games played"
    else:  # streaks
        filtered = [s for s in stats if s["current_streak"] > 3]
        title = "🔥 Current Streak Leaderboard"
        desc = "Only players with a streak > 3"

    # Sort ascending by Bayesian average (lower = better)
    filtered.sort(key=lambda s: s["bayes"])

    # Build leaderboard display
    lines = []
    for rank, s in enumerate(filtered, 1):
        lines.append(
            f"**{rank}. {s['name']}** — "
            f"Avg: {s['avg']:.2f} | "
            f"Streak: {s['current_streak']} | "
            f"Streak Avg: {s['streak_avg']:.2f} | "
            f"Compl: {s['completion']:.0f}% | "
            f"Longest: {s['longest_streak']} | "
            f"StdDev: {s['stddev']:.2f}"
        )

    if not lines:
        desc += "\n\n(No qualifying players yet.)"

    embed = discord.Embed(
        title=title,
        description=desc + "\n\n" + "\n".join(lines),
        color=discord.Color.gold() if show == "overall" else discord.Color.green(),
    )
    embed.set_footer(text=f"Sorted by Bayesian average (threshold={BAYESIAN_THRESHOLD}, hidden)")
    return embed

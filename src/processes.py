# processes.py
# Parses leaderboard messages, updates user stats, and builds leaderboards.

import re
import math
import statistics
import discord
from datetime import datetime

from storage import get_user_stats, save_user_stats

# --- CONSTANTS ---
LEADERBOARD_PATTERN = re.compile(
    r"\*\*Your group is on a (\d+) day streak!\*\*.*?Here are yesterday's results:(.*)",
    re.DOTALL,
)
RESULT_LINE_PATTERN = re.compile(r"([👑X]?)\s?(\d|X)/6:\s(.+)")

# --- WORDLE STATS UPDATE ---

async def parse_wordle_message(message, user_dict):
    """
    Parses only the official leaderboard messages and updates all mentioned users.
    Expected message format:
        **Your group is on a 6 day streak!** 🔥 Here are yesterday's results:
        👑 4/6: <@123> <@456>
        5/6: <@789>
        6/6: <@111>
        X/6: <@222>
    """

    if not message.content.startswith("**Your group is on"):
        return None

    match = LEADERBOARD_PATTERN.search(message.content)
    if not match:
        return None

    group_streak = int(match.group(1))
    results_text = match.group(2).strip()

    # Parse each line like "4/6: <@id> <@id>"
    for line in results_text.splitlines():
        res_match = RESULT_LINE_PATTERN.match(line.strip())
        if not res_match:
            continue

        _, score_text, mentions_text = res_match.groups()
        user_ids = re.findall(r"<@!?(\d+)>", mentions_text)

        for uid in user_ids:
            tries = 6 if score_text == "X" else int(score_text)
            success = score_text != "X"

            # Get or init user
            user_stats = user_dict.get(uid, {
                "user_id": uid,
                "games": 0,
                "wins": 0,
                "losses": 0,
                "total_tries": 0,
                "tries_list": [],
                "current_streak": 0,
                "longest_streak": 0,
            })

            # Update stats
            user_stats["games"] += 1
            user_stats["tries_list"].append(tries)

            if success:
                user_stats["wins"] += 1
                user_stats["current_streak"] += 1
                if user_stats["current_streak"] > user_stats["longest_streak"]:
                    user_stats["longest_streak"] = user_stats["current_streak"]
            else:
                user_stats["losses"] += 1
                user_stats["current_streak"] = 0

            user_stats["total_tries"] = sum(user_stats["tries_list"])

            user_dict[uid] = user_stats
            await save_user_stats(user_stats)

    return True


# --- STATISTICS HELPERS ---

def bayesian_average(mean, n, global_mean, threshold=10):
    """
    Bayesian average with threshold of 10.
    Weights user's mean toward global mean if they have few games.
    """
    return (threshold * global_mean + n * mean) / (threshold + n)


def calc_user_metrics(user_stats, global_mean):
    """Compute per-user metrics."""
    tries_list = user_stats.get("tries_list", [])
    n = len(tries_list)
    if n == 0:
        return None

    mean = sum(tries_list) / n
    stddev = statistics.stdev(tries_list) if n > 1 else 0
    completion = user_stats["wins"] / user_stats["games"] if user_stats["games"] else 0

    bayes = bayesian_average(mean, n, global_mean)
    return {
        "user_id": user_stats["user_id"],
        "avg": mean,
        "stddev": stddev,
        "completion": completion,
        "bayes_avg": bayes,
        "current_streak": user_stats["current_streak"],
        "longest_streak": user_stats["longest_streak"],
        "games": n,
    }


# --- LEADERBOARD BUILDER ---

def build_leaderboard_embed(user_dict, mode="global"):
    """
    Builds Discord embed for leaderboard.
    mode = "global" or "streak"
    """
    # Compute global mean
    all_means = []
    for u in user_dict.values():
        if len(u.get("tries_list", [])) > 0:
            all_means.append(sum(u["tries_list"]) / len(u["tries_list"]))
    global_mean = sum(all_means) / len(all_means) if all_means else 4.5

    # Compute metrics per user
    users_data = []
    for stats in user_dict.values():
        metrics = calc_user_metrics(stats, global_mean)
        if metrics:
            users_data.append(metrics)

    # Filter and sort
    if mode == "streak":
        users_data = [u for u in users_data if u["current_streak"] >= 3]
        users_data.sort(key=lambda x: (-x["current_streak"], x["avg"]))
        title = "🔥 Current Streak Leaderboard (≥3)"
    else:
        # Sort by Bayesian average (lower = better)
        users_data = [u for u in users_data if u["games"] >= 10]
        users_data.sort(key=lambda x: x["bayes_avg"])
        title = "🏆 Wordle Leaderboard"

    # Build embed
    embed = discord.Embed(
        title=title,
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )

    if not users_data:
        embed.description = "No qualifying players yet!"
        return embed

    # Prepare fields
    user_lines = []
    avg_lines = []
    streak_lines = []
    comp_lines = []
    std_lines = []
    long_lines = []

    for u in users_data[:20]:
        user_lines.append(f"<@{u['user_id']}>")
        avg_lines.append(f"{u['avg']:.2f}")
        streak_lines.append(str(u["current_streak"]))
        comp_lines.append(f"{u['completion']*100:.0f}%")
        std_lines.append(f"{u['stddev']:.2f}")
        long_lines.append(str(u["longest_streak"]))

    embed.add_field(name="User", value="\n".join(user_lines), inline=True)
    embed.add_field(name="Avg", value="\n".join(avg_lines), inline=True)
    embed.add_field(name="Streak", value="\n".join(streak_lines), inline=True)
    embed.add_field(name="Completion", value="\n".join(comp_lines), inline=True)
    embed.add_field(name="StdDev", value="\n".join(std_lines), inline=True)
    embed.add_field(name="Longest", value="\n".join(long_lines), inline=True)

    return embed

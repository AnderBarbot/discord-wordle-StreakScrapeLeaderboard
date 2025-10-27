# processes.py
# Parses leaderboard messages, updates user stats, and builds leaderboards.

import re
import statistics
import discord
from datetime import datetime
from storage import save_user_stats

LEADERBOARD_PATTERN = re.compile(
    r"\*\*Your group is on a (\d+) day streak!\*\*.*?Here are yesterday's results:(.*)",
    re.DOTALL,
)
RESULT_LINE_PATTERN = re.compile(r"([👑X]?)\s?(\d|X)/6:\s(.+)")


async def parse_wordle_message(message, user_dict):
    """
    Parses only the official leaderboard messages and updates all mentioned users.
    """
    """Parse only leaderboard messages in the standard format."""
    if not message.content.startswith("**Your group is on"):
        return

    match = LEADERBOARD_PATTERN.search(message.content)
    if not match:
        return

    results_text = match.group(2).strip()
    # Parse each line like "4/6: <@id> <@id>"
    for line in results_text.splitlines():
        m = RESULT_LINE_PATTERN.match(line.strip())
        if not m:
            continue
        _, score_text, mentions = m.groups()
        user_ids = re.findall(r"<@!?(\d+)>", mentions)
        tries = 6 if score_text == "X" else int(score_text)
        success = score_text != "X"

        for uid in user_ids:
            u = user_dict.get(uid, {
                "user_id": uid, "games": 0, "wins": 0, "losses": 0,
                "total_tries": 0, "tries_list": [],
                "current_streak": 0, "longest_streak": 0
            })
            u["games"] += 1
            u["tries_list"].append(tries)
            if success:
                u["wins"] += 1
                u["current_streak"] += 1
                u["longest_streak"] = max(u["longest_streak"], u["current_streak"])
            else:
                u["losses"] += 1
                u["current_streak"] = 0
            u["total_tries"] = sum(u["tries_list"])
            user_dict[uid] = u
            await save_user_stats(u)


def build_leaderboard_embed(user_dict, mode="global"):
    """Builds a simple Discord leaderboard embed."""
    data = []
    all_means = [sum(u["tries_list"]) / len(u["tries_list"])
                 for u in user_dict.values() if u["tries_list"]]
    global_mean = sum(all_means) / len(all_means) if all_means else 4.5

    for u in user_dict.values():
        if not u["tries_list"]:
            continue
        avg = sum(u["tries_list"]) / len(u["tries_list"])
        std = statistics.stdev(u["tries_list"]) if len(u["tries_list"]) > 1 else 0
        completion = u["wins"] / u["games"] if u["games"] else 0
        bayes = (10 * global_mean + len(u["tries_list"]) * avg) / (10 + len(u["tries_list"]))
        data.append({
            "id": u["user_id"], "avg": avg, "std": std, "completion": completion,
            "bayes": bayes, "streak": u["current_streak"], "longest": u["longest_streak"],
            "games": len(u["tries_list"])
        })

    if mode == "streak":
        data = [u for u in data if u["streak"] >= 3]
        data.sort(key=lambda x: (-x["streak"], x["avg"]))
        title = "🔥 Current Streak Leaderboard (≥3)"
    else:
        data = [u for u in data if u["games"] >= 10]
        data.sort(key=lambda x: x["bayes"])
        title = "🏆 Wordle Leaderboard"

    embed = discord.Embed(title=title, color=discord.Color.green(), timestamp=datetime.utcnow())
    if not data:
        embed.description = "No qualifying players yet!"
        return embed

    embed.add_field(name="User", value="\n".join(f"<@{u['id']}>" for u in data), inline=True)
    embed.add_field(name="Avg", value="\n".join(f"{u['avg']:.2f}" for u in data), inline=True)
    embed.add_field(name="Streak", value="\n".join(str(u['streak']) for u in data), inline=True)
    return embed

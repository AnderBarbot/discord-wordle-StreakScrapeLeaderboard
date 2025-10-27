import re
import asyncio
import statistics
import discord
from datetime import datetime
from storage import save_user_stats
import logging

# --- Config & Patterns ---
logger = logging.getLogger("wordle_bot")
GROUP_TRIGGER = "Your group is on"
RESULTS_MARKER = re.compile(r"Here are yesterday'?s results\s*:", re.IGNORECASE)
SCORE_PATTERN = re.compile(r"([1-6X])/6", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"<@!?(\d+)>")
BAYESIAN_THRESHOLD = 5

# --- Helper: Bayesian average ---
def _bayesian_avg(mean, n, global_mean, threshold=BAYESIAN_THRESHOLD):
    return (threshold * global_mean + n * mean) / (threshold + n)

# --- Core Parser ---
async def parse_wordle_message(message, user_dict):
    """Parse a Wordle message, update user stats, and return number of entries parsed."""
    content = message.content.strip()
    logger.debug(f"[Parser] Processing message {message.id}")

    marker = RESULTS_MARKER.search(content)
    if not marker:
        logger.debug("[Parser] No results marker found")
        return 0

    lines = content[marker.end():].strip().splitlines()
    parsed = 0
    mentioned_users = set()

    for line in lines:
        score_match = SCORE_PATTERN.search(line)
        if not score_match:
            continue

        score = score_match.group(1).upper()
        success = score != "X"
        tries = 6 if score == "X" else int(score)

        # --- Identify users ---
        user_ids = MENTION_PATTERN.findall(line)
        usernames = [name[1:] for name in line.split() if name.startswith("@") and not name[1:].isdigit()]
        all_users = []

        # Resolve user mentions
        if message.guild:
            for uid in user_ids:
                member = message.guild.get_member(int(uid))
                username = member.display_name if member else f"user-{uid}"
                all_users.append((str(uid), username))

            for name in usernames:
                member = next((m for m in message.guild.members if m.display_name.lower() == name.lower()), None)
                if member:
                    uid = str(member.id)
                    username = member.display_name
                else:
                    uid = f"user-{name}"
                    username = name
                all_users.append((uid, username))

        if not all_users:
            continue

        # --- Update user stats ---
        for uid, username in all_users:
            mentioned_users.add(uid)
            u = user_dict.get(uid, {
                "user_id": uid,
                "username": username,
                "games": 0,
                "wins": 0,
                "losses": 0,
                "tries_list": [],
                "current_streak": 0,
                "longest_streak": 0
            })

            u["username"] = username
            u["games"] += 1
            u["tries_list"].append(tries)

            if success:
                u["wins"] += 1
            else:
                u["losses"] += 1

            # Increment streak for any result
            u["current_streak"] += 1
            u["longest_streak"] = max(u["longest_streak"], u["current_streak"])

            user_dict[uid] = u

            # Save asynchronously
            try:
                await asyncio.to_thread(save_user_stats, u)
            except Exception as e:
                logger.exception(f"[DB] Failed to save user {uid}: {e}")

            parsed += 1

    # --- Handle skipped users ---
    for uid, u in user_dict.items():
        if uid not in mentioned_users:
            u["current_streak"] = 0  # skipped day breaks streak

    return parsed

# --- Leaderboard Builder ---
async def build_leaderboard_embed(user_dict, guild=None):
    rows = []

    # Global mean
    total_tries = sum(sum(u["tries_list"]) for u in user_dict.values() if u.get("tries_list"))
    total_count = sum(len(u["tries_list"]) for u in user_dict.values() if u.get("tries_list"))
    global_mean = (total_tries / total_count) if total_count else 4.5

    for u in user_dict.values():
        tries_list = u.get("tries_list", [])
        n = len(tries_list)
        if n == 0:
            continue

        avg = sum(tries_list) / n
        std = statistics.stdev(tries_list) if n > 1 else 0
        adj_avg = _bayesian_avg(avg, n, global_mean)

        rows.append({
            "id": u["user_id"],
            "username": u.get("username", f"user-{u['user_id']}"),
            "avg": avg,
            "adj_avg": adj_avg,
            "std": std,
            "games": n,
            "losses": u["losses"],
            "streak": u["current_streak"],
            "longest": u["longest_streak"]
        })

    if not rows:
        return discord.Embed(title="🏆 Wordle Leaderboard", description="No data yet!")

    # Sort by Bayesian average
    rows.sort(key=lambda r: r["adj_avg"])

    header = f"{'User':<10}{'Avg':>8}{'Adj-Avg':>8}{'Games':>6}{'Loss':>6}{'Streak':>8}{'Longest':>8}"
    lines = [header, "─" * len(header)]
    for r in rows:
        member = guild.get_member(int(r["id"])) if guild else None
        name = (member.display_name if member else r["username"])[:15]
        line = f"{name:<10}{r['avg']:>8.2f}{r['adj_avg']:>8.2f}{r['games']:>6}{r['losses']:>6}{r['streak']:>8}{r['longest']:>8}"
        lines.append(line)

    embed = discord.Embed(
        title="🏆 Wordle Leaderboard",
        description=f"```\n{chr(10).join(lines)}\n```",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Sorted by Bayesian average (threshold={BAYESIAN_THRESHOLD})")
    return embed

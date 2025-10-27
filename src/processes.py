import re
import asyncio
import statistics
import discord
from datetime import datetime
from storage import save_user_stats
import logging

# --- Parsing Patterns ---
GROUP_TRIGGER = "Your group is on"
RESULTS_MARKER = re.compile(r"Here are yesterday'?s results\s*:", re.IGNORECASE)
SCORE_PATTERN = re.compile(r"([1-6X])/6", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"<@!?(\d+)>")
BAYESIAN_THRESHOLD = 10

logger = logging.getLogger("wordle_bot")

# --- Core Parser ---
async def parse_wordle_message(message, user_dict):
    content = message.content.strip()
    logger.debug(f"[Parser] Processing message {message.id}: {content.replace(chr(10),' ')}")
    marker = RESULTS_MARKER.search(content)
    if not marker:
        logger.debug(f"[Parser] No results marker found in message {message.id}")
        return 0

    lines = content[marker.end():].strip().splitlines()
    parsed = 0

    for line in lines:
        match = SCORE_PATTERN.search(line)
        if not match:
            logger.debug(f"[Parser] No score pattern matched in line: {line}")
            continue

        score = match.group(1).upper()
        success = score != "X"
        tries = 6 if score == "X" else int(score)
        user_ids = MENTION_PATTERN.findall(line)

        if not user_ids:
            logger.debug(f"[Parser] No user mentions found in line: {line}")
            continue

        for uid in user_ids:
            member = message.guild.get_member(int(uid)) if message.guild else None
            username = member.display_name if member else f"user-{uid}"

            u = user_dict.get(uid, {
                "user_id": uid,
                "username": username,
                "games": 0, "wins": 0, "losses": 0,
                "tries_list": [],
                "current_streak": 0, "longest_streak": 0
            })
            u["username"] = username
            u["games"] += 1
            u["tries_list"].append(tries)
            if success:
                u["wins"] += 1
                u["current_streak"] += 1
                u["longest_streak"] = max(u["longest_streak"], u["current_streak"])
            else:
                u["losses"] += 1
                u["current_streak"] = 0

            user_dict[uid] = u
            logger.info(f"[Parser] Parsed {uid} ({username}): score={score}, tries={tries}, success={success}")
            try:
                await asyncio.to_thread(save_user_stats, u)
                logger.debug(f"[DB] Saved user {uid} stats successfully")
            except Exception as e:
                logger.exception(f"[DB] Failed to save user {uid} stats: {e}")
            parsed += 1

    logger.debug(f"[Parser] Finished parsing message {message.id}, total parsed entries: {parsed}")
    return parsed


def _bayesian_avg(mean, n, global_mean, threshold=BAYESIAN_THRESHOLD):
    return (threshold * global_mean + n * mean) / (threshold + n)


async def build_leaderboard_embed(user_dict, guild=None):
    rows = []

    #global mean calculation
    total_success_tries = 0
    total_success_count = 0
    for u in user_dict.values():
        tries_list = u.get("tries_list", []) or []
        total_success_tries += sum(tries_list)
        total_success_count += len(tries_list)
    global_mean = (total_success_tries / total_success_count) if total_success_count else 4.5

    for u in user_dict.values():
        n = len(u["tries_list"])
        if n == 0:
            continue
        avg = sum(u["tries_list"]) / n
        std = statistics.stdev(u["tries_list"]) if n > 1 else 0
        bayes = _bayesian_avg(avg, n, global_mean)

        rows.append({
            "id": u["user_id"],
            "username": u.get("username", f"user-{u['user_id']}"),
            "avg": avg, "adj_avg": bayes, "std": std,
            "games": n, "losses": u["losses"],
            "streak": u["current_streak"], "longest": u["longest_streak"]
        })

    if not rows:
        return discord.Embed(title="🏆 Wordle Leaderboard", description="No data yet!")

    rows.sort(key=lambda r: r["adj_avg"])

    header = f"{'User':<10}{'Avg':>8}{'Adj-Avg':>9}{'Games':>7}{'Loss':>7}{'Streak':>8}{'Longest':>9}"
    lines = [header, "─" * len(header)]

    for r in rows:
        member = guild.get_member(int(r["id"])) if guild else None
        name = (member.display_name if member else r["username"])[:15]
        line = f"{name:<10}{r['avg']:>8.2f}{r['adj_avg']:>9.2f}{r['games']:>7}{r['losses']:>7}{r['streak']:>8}{r['longest']:>9}"
        lines.append(line)

    embed = discord.Embed(
        title="🏆 Wordle Leaderboard",
        description=f"```\n{chr(10).join(lines)}\n```",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Sorted by Bayesian average (threshold={BAYESIAN_THRESHOLD})")
    return embed
    
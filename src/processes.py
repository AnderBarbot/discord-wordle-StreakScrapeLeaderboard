import re
import asyncio
import statistics
import discord
from datetime import datetime, timedelta
from storage import save_user_stats, mark_message_processed, message_already_processed
import logging

"""
processes.py
---------------
Core parsing and leaderboard logic for the Wordle Discord Bot.
Responsible for detecting valid Wordle result messages,
extracting player performance data, updating user stats,
and generating leaderboard embeds for Discord display.
"""

# --- Config & Patterns ---
logger = logging.getLogger("wordle_bot")
GROUP_TRIGGER = "Your group is on"
RESULTS_MARKER = re.compile(r"Here are yesterday'?s results\s*:", re.IGNORECASE)
SCORE_PATTERN = re.compile(r"([1-6X])/6", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"<@!?(\d+)>")
CHEATER_PATTERN = re.compile(r"<@!?(\d+)>.*\bcheated\b", re.IGNORECASE)
BAYESIAN_THRESHOLD = 5
CHEATER_SCORE = 6
FAILURE_SCORE = 6
ENABLE_HANDICAP_CAP = True #if true, handicap affect stops at global mean. 

# orchestrates message handling
async def handle_all_messages(message, user_dict):
    if message_already_processed(message.id):
        logger.debug(f"[Handle] Message {message.id} already processed")
        return 0

    parsed = 0
    try:
        # Normal Wordle messages
        if GROUP_TRIGGER in message.content:
            parsed = await parse_wordle_message(message, user_dict)
        if parsed:
            mark_message_processed(message.id)
            logger.debug(f"[Handle] Message {message.id} processed and marked")
        else:
            logger.debug(f"[Handle] Message {message.id} contained no valid data")

    except Exception as e:
        logger.exception(f"[Handle] Error handling message {message.id}: {e}")
    return parsed

# wordle bot leaderboard message parsing
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
    global_mean = _global_average(user_dict)

    for line in lines:
        score_match = SCORE_PATTERN.search(line)
        if not score_match:
            continue

        score = score_match.group(1).upper()
        success = score != "X"
        tries = FAILURE_SCORE if score == "X" else int(score)

        # --- Identify users ---
        user_ids = MENTION_PATTERN.findall(line)
        usernames = [name[1:] for name in line.split() if name.startswith("@") and not name[1:].isdigit()]
        all_users = []

        # handles both ID and username/alias mentions
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

        # retrieve then update user stats
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
                "longest_streak": 0,
                "handicap": 0.0 
            })

            u["username"] = username
            u["games"] += 1

            #apply handicap
            if ENABLE_HANDICAP_CAP:
                if u["handicap"] == 0:
                    pass
                elif u["handicap"] > 0:
                    tries = min(global_mean, tries + u["handicap"])
                elif u["handicap"] < 0:
                    tries = max(global_mean, tries + u["handicap"])
            else:
                tries += u["handicap"]
            u["tries_list"].append(tries)

            if success:
                u["wins"] += 1
            else:
                u["losses"] += 1

            u["current_streak"] += 1
            u["longest_streak"] = max(u["longest_streak"], u["current_streak"])

            user_dict[uid] = u

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

# bayesian averages takes the users scores, then adds x average scores from your overall server before calculating the mean "user score".
# effectively pulls everyone towards the mean. users with many scores can resist the pull better. 
def _bayesian_avg(mean, n, global_mean, threshold=BAYESIAN_THRESHOLD):
    return (threshold * global_mean + n * mean) / (threshold + n)

def _global_average(user_dict):
    total_tries = sum(sum(u["tries_list"]) for u in user_dict.values() if u.get("tries_list"))
    total_count = sum(len(u["tries_list"]) for u in user_dict.values() if u.get("tries_list"))
    return (total_tries / total_count) if total_count else 4.5

#builds leaderboard embed, hopefully readable as 1 line per user in discord
async def build_leaderboard_embed(user_dict, guild=None):
    rows = []
    global_mean = _global_average(user_dict)

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
            "longest": u["longest_streak"],
            "handicap": u["handicap"]
        })

    if not rows:
        return discord.Embed(title="🏆 Wordle Leaderboard", description="No data yet!")

    rows.sort(key=lambda r: r["adj_avg"])

    header = "User     Avg  AdjA  Std  W  L  Stk Lng Hnd"
    lines = [header, "─" * len(header)]

    for r in rows:
        #retrive nickname
        member = guild.get_member(int(r["id"])) if guild else None
        name = (member.display_name if member else r["username"])[:8]

        line = (
            f"{name:<8} "
            f"{r['avg']:5.2f} "
            f"{r['adj_avg']:5.2f} "
            f"{r['std']:4.2f} "
            f"{r['games']:>2d} "
            f"{r['losses']:>2d} "
            f"{r['streak']:>3d} "
            f"{r['longest']:>3d} "
            f"{r['handicap']:4.2f}"
        )
        lines.append(line)

    embed = discord.Embed(
        title="🏆 Wordle Leaderboard",
        description=f"```\n{chr(10).join(lines)}\n```",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow() - timedelta(hours=7)
    )
    embed.set_footer(text=f"Sorted by Bayesian avg (threshold={BAYESIAN_THRESHOLD})")
    return embed

# set handicap for a user
async def set_handicap(user_id: str, handicap: float, user_dict: dict):
    if user_id not in user_dict:
        return False
    u = user_dict[user_id]
    u["handicap"] = handicap
    user_dict[user_id] = u
    await asyncio.to_thread(save_user_stats, u)
    logger.info(f"[Handicap] Set handicap {handicap} for user {u['username']}")
    return True

    #set user's lowest score to a given value
async def set_user_lowest_score(user_id: str, new_score: int, user_dict: dict):
    if user_id not in user_dict:
        logger.warning(f"[CheaterCmd] User {user_id} not found in user_dict")
        return False
    u = user_dict[user_id]
    tries = u.get("tries_list")
    if not tries:
        logger.warning(f"[CheaterCmd] User {u['username']} has no tries_list to modify.")
        return False

    lowest_idx = tries.index(min(tries))
    old_score = tries[lowest_idx]
    tries[lowest_idx] = new_score
    user_dict[user_id] = u
    
    await asyncio.to_thread(save_user_stats, u)
    logger.info(f"[CheaterCmd] Replaced {u['username']}'s lowest score ({old_score}) with {new_score}")
    return True
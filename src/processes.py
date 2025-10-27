import re
import asyncio
import statistics
import discord
from datetime import datetime
from storage import save_user_stats

# --- Parsing Patterns ---
SCORE_PATTERN = re.compile(r"([1-6X])/6", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"<@!?(\d+)>")

BAYESIAN_THRESHOLD = 10

async def parse_wordle_message(message, user_dict):
    content = message.content.strip()
    marker = re.search(r"Here are yesterday'?s results\s*:", content, re.IGNORECASE)
    if not marker:
        return 0
    lines = content[marker.end():].strip().splitlines()

    parsed = 0
    for line in lines:
        match = SCORE_PATTERN.search(line)
        if not match:
            continue
        score = match.group(1).upper()
        success = score != "X"
        tries = 6 if score == "X" else int(score)

        user_ids = MENTION_PATTERN.findall(line)
        for uid in user_ids:
            # Try to resolve to Discord member (guild cache)
            member = None
            try:
                member = message.guild.get_member(int(uid)) if getattr(message, "guild", None) else None
            except Exception:
                member = None

            # Create/merge record. Do NOT insert a "User-<id>" fallback name here.
            u = user_dict.get(uid, {
                "user_id": uid,
                # "name" intentionally not set here unless we resolved member
                "games": 0, "wins": 0, "losses": 0,
                "tries_list": [],
                "current_streak": 0, "longest_streak": 0
            })

            if member:
                u["name"] = member.display_name  # only set when we actually resolved

            # Update stats
            u["games"] = u.get("games", 0) + 1
            # keep current behavior for tries (if you want X/6 not to append, change here)
            u["tries_list"].append(6 if score == "X" else int(score))
            if success:
                u["wins"] = u.get("wins", 0) + 1
                u["current_streak"] = u.get("current_streak", 0) + 1
                u["longest_streak"] = max(u.get("longest_streak", 0), u["current_streak"])
            else:
                u["losses"] = u.get("losses", 0) + 1
                u["current_streak"] = 0

            user_dict[uid] = u
            await asyncio.to_thread(save_user_stats, u)
            parsed += 1
    return parsed



def _bayesian_avg(mean, n, global_mean, threshold=BAYESIAN_THRESHOLD):
    return (threshold * global_mean + n * mean) / (threshold + n)


def build_leaderboard_embed(user_dict):
    rows = []

    # Weighted global mean: sum(successful tries) / count(successful tries)
    total_success_tries = 0
    total_success_count = 0
    for u in user_dict.values():
        tries_list = u.get("tries_list", []) or []
        total_success_tries += sum(tries_list)
        total_success_count += len(tries_list)
    global_mean = (total_success_tries / total_success_count) if total_success_count else 4.5

    for u in user_dict.values():
        tries = u.get("tries_list", []) or []
        # Skip entirely if no games recorded
        if u.get("games", 0) == 0 and not tries:
            continue

        # avg/std are computed only over successful attempts (tries_list)
        avg = (sum(tries) / len(tries)) if tries else None
        std = statistics.stdev(tries) if len(tries) > 1 else 0.0
        n_success = len(tries)
        adj = _bayesian_avg(avg if avg is not None else global_mean, n_success, global_mean)

        # Use stored 'games' field (counts wins+losses) if present; otherwise estimate
        games = u.get("games", n_success + u.get("losses", 0))

        rows.append({
            "id": u["user_id"],
            "name": u.get("name"),        # may be None
            "avg": avg,
            "adj_avg": adj,
            "std": std,
            "games": games,
            "losses": u.get("losses", 0),
            "streak": u.get("current_streak", 0),
            "longest": u.get("longest_streak", 0),
            "n_success": n_success,
        })

    if not rows:
        return discord.Embed(title="🏆 Wordle Leaderboard", description="No data yet!")

    # sort by Bayesian-adjusted avg (lower is better)
    rows.sort(key=lambda r: (r["adj_avg"], (r["avg"] if r["avg"] is not None else 999), -r["n_success"]))

    # Header and fixed-width columns
    header = f"{'User':<20}{'Avg':>7}{'Adj':>7}{'Games':>7}{'L':>4}{'Stk':>5}{'Lng':>5}"
    lines = [header, "─" * len(header)]

    for r in rows:
        # prefer real name if available, otherwise show the raw id (no 'User-' prefix)
        name = (r["name"][:20] if r.get("name") else f"{r['id']}")
        avg_text = f"{r['avg']:.2f}" if r['avg'] is not None else "N/A"
        lines.append(f"{name:<20}{avg_text:>7}{r['adj_avg']:>7.2f}{r['games']:>7}{r['losses']:>4}{r['streak']:>5}{r['longest']:>5}")

    description = "```\n" + "\n".join(lines) + "\n```"
    embed = discord.Embed(title="🏆 Wordle Leaderboard", description=description, color=discord.Color.gold(), timestamp=datetime.utcnow())
    embed.set_footer(text=f"Sorted by Bayesian average (threshold={BAYESIAN_THRESHOLD})")
    return embed


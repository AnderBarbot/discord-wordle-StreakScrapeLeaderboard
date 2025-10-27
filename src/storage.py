# storage.py
# Minimal SQLite storage for user Wordle stats.

import sqlite3
import json
import asyncio

DB_PATH = "wordle.db"

# --- Initialize database ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            games INTEGER,
            wins INTEGER,
            losses INTEGER,
            total_tries INTEGER,
            tries_list TEXT,
            current_streak INTEGER,
            longest_streak INTEGER
        )
    """)
    conn.commit()
    conn.close()


# --- Helpers ---
def _connect():
    return sqlite3.connect(DB_PATH)


async def save_user_stats(user_stats):
    """Insert or update user stats."""
    conn = _connect()
    c = conn.cursor()

    c.execute("""
        INSERT INTO users (user_id, games, wins, losses, total_tries, tries_list, current_streak, longest_streak)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            games=excluded.games,
            wins=excluded.wins,
            losses=excluded.losses,
            total_tries=excluded.total_tries,
            tries_list=excluded.tries_list,
            current_streak=excluded.current_streak,
            longest_streak=excluded.longest_streak
    """, (
        user_stats["user_id"],
        user_stats["games"],
        user_stats["wins"],
        user_stats["losses"],
        user_stats["total_tries"],
        json.dumps(user_stats["tries_list"]),
        user_stats["current_streak"],
        user_stats["longest_streak"],
    ))
    conn.commit()
    conn.close()


def load_all_users():
    """Load all users as dict of dicts."""
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    conn.close()

    data = {}
    for r in rows:
        data[r[0]] = {
            "user_id": r[0],
            "games": r[1],
            "wins": r[2],
            "losses": r[3],
            "total_tries": r[4],
            "tries_list": json.loads(r[5]) if r[5] else [],
            "current_streak": r[6],
            "longest_streak": r[7],
        }
    return data

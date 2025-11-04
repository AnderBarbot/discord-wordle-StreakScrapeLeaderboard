import sqlite3, json

"""
storage.py
------------
Handles all persistent storage for the Wordle Discord Bot.
Creates and manages the SQLite database, including user stats
and processed message tracking to prevent duplicate parsing.
"""

DB_PATH = "wordle.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            games INTEGER,
            wins INTEGER,
            losses INTEGER,
            tries_list TEXT,
            current_streak INTEGER,
            longest_streak INTEGER
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_messages (
            message_id TEXT PRIMARY KEY
        )
        """)

# --- User Data ---
def save_user_stats(u):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO users (user_id, username, games, wins, losses, tries_list, current_streak, longest_streak)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            games=excluded.games,
            wins=excluded.wins,
            losses=excluded.losses,
            tries_list=excluded.tries_list,
            current_streak=excluded.current_streak,
            longest_streak=excluded.longest_streak
        """, (
            u["user_id"], u.get("username"),
            u["games"], u["wins"], u["losses"],
            json.dumps(u["tries_list"]),
            u["current_streak"], u["longest_streak"]
        ))

def load_all_users():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
    users = {}
    for r in rows:
        users[r[0]] = {
            "user_id": r[0],
            "username": r[1],
            "games": r[2],
            "wins": r[3],
            "losses": r[4],
            "tries_list": json.loads(r[5]) if r[5] else [],
            "current_streak": r[6],
            "longest_streak": r[7],
        }
    return users

def clear_all_users():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM processed_messages")

# --- Message Tracking ---
def message_already_processed(message_id):
    with sqlite3.connect(DB_PATH) as conn:
        res = conn.execute("SELECT 1 FROM processed_messages WHERE message_id=?", (str(message_id),)).fetchone()
    return res is not None

def mark_message_processed(message_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO processed_messages (message_id) VALUES (?)", (str(message_id),))

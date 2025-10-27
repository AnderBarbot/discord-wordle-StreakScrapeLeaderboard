import sqlite3, json

DB_PATH = "wordle.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            games INTEGER,
            wins INTEGER,
            losses INTEGER,
            tries_list TEXT,
            current_streak INTEGER,
            longest_streak INTEGER
        )""")

def save_user_stats(u):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO users (user_id, games, wins, losses, tries_list, current_streak, longest_streak)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            games=excluded.games,
            wins=excluded.wins,
            losses=excluded.losses,
            tries_list=excluded.tries_list,
            current_streak=excluded.current_streak,
            longest_streak=excluded.longest_streak
        """, (u["user_id"], u["games"], u["wins"], u["losses"], json.dumps(u["tries_list"]), u["current_streak"], u["longest_streak"]))

def load_all_users():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
    users = {}
    for r in rows:
        users[r[0]] = {
            "user_id": r[0],
            "games": r[1],
            "wins": r[2],
            "losses": r[3],
            "tries_list": json.loads(r[4]),
            "current_streak": r[5],
            "longest_streak": r[6],
        }
    return users

def clear_all_users():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM users")

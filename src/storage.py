#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# storage.py — Asynchronous persistence for Wordle bot data.

import aiosqlite
import json
from User import User
from WordleResult import WordleResult


DB_FILE = "wordlebot.db"


async def init_db():
    """Initialize database tables if they don't exist."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)
        await db.commit()


async def save_user(user: User):
    """Store a user's data (entire record) in the database."""
    data_json = json.dumps(user.to_dict(), ensure_ascii=False)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT INTO users (user_id, name, data)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET name=excluded.name, data=excluded.data
        """, (str(getattr(user.author, "id", user.display_name)), user.display_name, data_json))
        await db.commit()


async def load_user(user_id, author=None):
    """Fetch a user from the database; returns User or None."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT data FROM users WHERE user_id = ?", (str(user_id),)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            data = json.loads(row[0])
            return User.from_dict(data, author=author)


async def load_all_users():
    """Load all users into memory as User objects."""
    users = {}
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, data FROM users") as cursor:
            async for row in cursor:
                uid, data_json = row
                data = json.loads(data_json)
                users[uid] = User.from_dict(data)
    return users


async def save_all_users(users: dict):
    """Save all users in one go."""
    async with aiosqlite.connect(DB_FILE) as db:
        for uid, user in users.items():
            data_json = json.dumps(user.to_dict(), ensure_ascii=False)
            await db.execute("""
                INSERT INTO users (user_id, name, data)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET name=excluded.name, data=excluded.data
            """, (str(uid), user.display_name, data_json))
        await db.commit()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# WordleResult.py — Stores individual Wordle attempt info.

from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass(frozen=True)
class WordleResult:
    number: int
    tries: int
    hard: bool
    post_time: datetime
    grid: list  # Optional: the emoji grid, currently unused

    def to_dict(self):
        return {
            "number": self.number,
            "tries": self.tries,
            "hard": self.hard,
            "post_time": self.post_time.isoformat() if self.post_time else None,
            "grid": self.grid,
        }

    @classmethod
    def from_dict(cls, data):
        post_time = None
        if isinstance(data.get("post_time"), str):
            try:
                post_time = datetime.fromisoformat(data["post_time"])
            except Exception:
                post_time = None
        return cls(
            number=data["number"],
            tries=data["tries"],
            hard=data.get("hard", False),
            post_time=post_time,
            grid=data.get("grid", []),
        )

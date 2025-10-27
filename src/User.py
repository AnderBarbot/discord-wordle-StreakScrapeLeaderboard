#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# User.py — Represents a single Wordle player and their game history.

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from WordleResult import WordleResult


@dataclass
class User:
    """Represents a Discord user participating in Wordle."""
    author: any  # discord.Member or discord.User
    results: List[WordleResult] = field(default_factory=list)
    played_nums: List[int] = field(default_factory=list)
    total_games: int = 0

    @property
    def display_name(self):
        return getattr(self.author, "display_name", str(self.author))

    def add_result(self, result: WordleResult):
        """Insert a result and keep the list sorted."""
        if result.number in self.played_nums:
            return False
        self.results.append(result)
        self.results.sort(key=lambda r: r.number)
        self.played_nums.append(result.number)
        self.total_games += 1
        return True

    def last_result(self) -> Optional[WordleResult]:
        return self.results[-1] if self.results else None

    def to_dict(self) -> dict:
        """Serialize user for DB or JSON."""
        return {
            "id": getattr(self.author, "id", None),
            "name": self.display_name,
            "total_games": self.total_games,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, data, author=None):
        """Deserialize user from stored record."""
        u = cls(author=author or data.get("name"))
        u.total_games = data.get("total_games", 0)
        u.results = [WordleResult.from_dict(r) for r in data.get("results", [])]
        u.played_nums = [r.number for r in u.results]
        return u

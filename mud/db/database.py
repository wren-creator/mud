import hashlib
import json
import logging
import os
import sqlite3
from typing import Optional

log = logging.getLogger(__name__)

DB_PATH = "data/mud.db"


def _get_conn() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                name     TEXT PRIMARY KEY,
                pw_hash  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS players (
                name TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
        """)


_init_db()


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class Database:
    @staticmethod
    def save_player(player, password: Optional[str] = None):
        from entities.player import Player
        data = json.dumps(player.to_dict())
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO players (name, data) VALUES (?, ?)",
                (player.name, data)
            )
            if password:
                conn.execute(
                    "INSERT OR REPLACE INTO accounts (name, pw_hash) VALUES (?, ?)",
                    (player.name, _hash(password))
                )

    @staticmethod
    def load_player(name: str) -> Optional["Player"]:
        from entities.player import Player
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT data FROM players WHERE name = ?", (name,)
            ).fetchone()
        if row:
            return Player.from_dict(json.loads(row["data"]))
        return None

    @staticmethod
    def check_password(name: str, password: str) -> bool:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT pw_hash FROM accounts WHERE name = ?", (name,)
            ).fetchone()
        if not row:
            return False
        return row["pw_hash"] == _hash(password)

    @staticmethod
    def account_exists(name: str) -> bool:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM accounts WHERE name = ?", (name,)
            ).fetchone()
        return row is not None

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence, Optional


@dataclass
class FriendRecord:
    chat_id: int
    steam_id: str
    public_id: Optional[str]
    alias: Optional[str]
    last_player_name: Optional[str]
    last_in_deadlock: bool
    entered_deadlock_at: Optional[int]

    @property
    def display_name(self) -> str:
        return self.alias or self.last_player_name or self.public_id or "unknown"


class FriendRepository(Protocol):
    def add_friend(self, chat_id: int, steam_id: str, public_id: Optional[str], alias: Optional[str]) -> None:
        ...

    def remove_friend(self, chat_id: int, steam_id: str) -> int:
        ...

    def list_friends(self, chat_id: int) -> Sequence[FriendRecord]:
        ...

    def get_all_friends(self) -> Sequence[FriendRecord]:
        ...

    def update_status(self, chat_id: int, steam_id: str, player_name: str, in_deadlock: bool) -> None:
        ...


class SQLiteFriendRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS friends (
                    chat_id INTEGER NOT NULL,
                    steam_id TEXT NOT NULL,
                    public_id TEXT,
                    alias TEXT,
                    last_player_name TEXT,
                    last_in_deadlock INTEGER NOT NULL DEFAULT 0,
                    entered_deadlock_at INTEGER,
                    PRIMARY KEY (chat_id, steam_id)
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(friends)").fetchall()
            }
            if "public_id" not in columns:
                connection.execute("ALTER TABLE friends ADD COLUMN public_id TEXT")
            if "entered_deadlock_at" not in columns:
                connection.execute("ALTER TABLE friends ADD COLUMN entered_deadlock_at INTEGER")

    def add_friend(self, chat_id: int, steam_id: str, public_id: Optional[str], alias: Optional[str]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO friends (chat_id, steam_id, public_id, alias)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, steam_id)
                DO UPDATE SET public_id = excluded.public_id, alias = excluded.alias
                """,
                (chat_id, steam_id, public_id, alias),
            )

    def remove_friend(self, chat_id: int, steam_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM friends WHERE chat_id = ? AND steam_id = ?",
                (chat_id, steam_id),
            )
            return cursor.rowcount

    def list_friends(self, chat_id: int) -> list[FriendRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chat_id, steam_id, public_id, alias, last_player_name, last_in_deadlock, entered_deadlock_at
                FROM friends
                WHERE chat_id = ?
                ORDER BY COALESCE(alias, last_player_name, public_id, steam_id)
                """,
                (chat_id,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_all_friends(self) -> list[FriendRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT chat_id, steam_id, public_id, alias, last_player_name, last_in_deadlock, entered_deadlock_at
                FROM friends
                ORDER BY chat_id, steam_id
                """
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def update_status(self, chat_id: int, steam_id: str, player_name: str, in_deadlock: bool) -> None:
        with self._connect() as connection:
            current_state_row = connection.execute(
                """
                SELECT last_in_deadlock, entered_deadlock_at
                FROM friends
                WHERE chat_id = ? AND steam_id = ?
                """,
                (chat_id, steam_id),
            ).fetchone()

            entered_deadlock_at = None
            if in_deadlock:
                previous_in_deadlock = bool(current_state_row["last_in_deadlock"]) if current_state_row else False
                previous_entered_deadlock_at = (
                    current_state_row["entered_deadlock_at"] if current_state_row else None
                )
                entered_deadlock_at = previous_entered_deadlock_at or int(time.time())

                if not previous_in_deadlock:
                    entered_deadlock_at = int(time.time())

            connection.execute(
                """
                UPDATE friends
                SET last_player_name = ?, last_in_deadlock = ?, entered_deadlock_at = ?
                WHERE chat_id = ? AND steam_id = ?
                """,
                (player_name, int(in_deadlock), entered_deadlock_at, chat_id, steam_id),
            )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> FriendRecord:
        return FriendRecord(
            chat_id=int(row["chat_id"]),
            steam_id=str(row["steam_id"]),
            public_id=row["public_id"],
            alias=row["alias"],
            last_player_name=row["last_player_name"],
            last_in_deadlock=bool(row["last_in_deadlock"]),
            entered_deadlock_at=row["entered_deadlock_at"],
        )


def create_friend_repository(backend: str, database_path: str) -> FriendRepository:
    normalized_backend = backend.strip().lower()
    if normalized_backend == "sqlite":
        return SQLiteFriendRepository(database_path)
    raise ValueError(f"Unsupported storage backend: {backend}")

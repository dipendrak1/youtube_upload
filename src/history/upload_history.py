"""SQLite persistence for uploaded video history."""

from pathlib import Path
import sqlite3
from typing import Any


class UploadHistoryRepository:
    """Store upload records in a local SQLite database."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    youtube_video_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    file_path TEXT,
                    file_hash TEXT,
                    file_size INTEGER,
                    category TEXT,
                    playlist_id TEXT,
                    uploaded_at TEXT,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_uploads_file_hash "
                "ON uploads(file_hash)"
            )

    def upsert(self, record: dict[str, Any]) -> None:
        columns = (
            "youtube_video_id",
            "title",
            "file_path",
            "file_hash",
            "file_size",
            "category",
            "playlist_id",
            "uploaded_at",
            "status",
            "source",
        )
        values = [record.get(column) for column in columns]
        assignments = ", ".join(
            f"{column}=excluded.{column}"
            for column in columns
            if column != "youtube_video_id"
        )
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO uploads ({', '.join(columns)})
                VALUES ({', '.join('?' for _ in columns)})
                ON CONFLICT(youtube_video_id) DO UPDATE SET {assignments}
                """,
                values,
            )

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM uploads").fetchone()
        return int(row["count"])

    def report(self, recent_limit: int = 10) -> dict[str, Any]:
        """Return aggregate counts and the most recent history records."""
        with self._connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) AS count FROM uploads"
            ).fetchone()["count"]
            grouped_queries = {
                "status": "SELECT status AS name, COUNT(*) AS count "
                "FROM uploads GROUP BY status ORDER BY status",
                "category": "SELECT COALESCE(category, '') AS name, COUNT(*) AS count "
                "FROM uploads GROUP BY category ORDER BY category",
                "source": "SELECT source AS name, COUNT(*) AS count "
                "FROM uploads GROUP BY source ORDER BY source",
            }
            groups = {
                group_name: [dict(row) for row in connection.execute(query)]
                for group_name, query in grouped_queries.items()
            }
            recent = [
                dict(row)
                for row in connection.execute(
                    "SELECT title, youtube_video_id, category, status, uploaded_at "
                    "FROM uploads ORDER BY uploaded_at DESC, id DESC LIMIT ?",
                    (recent_limit,),
                )
            ]

        return {"total": int(total), **groups, "recent": recent}

    def find_successful_by_hash(self, file_hash: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM uploads WHERE file_hash = ? AND status = 'uploaded' "
                "LIMIT 1",
                (file_hash,),
            ).fetchone()
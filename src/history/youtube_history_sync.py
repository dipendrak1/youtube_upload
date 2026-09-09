"""Synchronize YouTube uploads and local uploaded files into SQLite."""

import hashlib
import logging
from pathlib import Path
from typing import Any

from src.settings import Settings
from src.history.upload_history import UploadHistoryRepository


LOGGER = logging.getLogger(__name__)


class YouTubeHistorySynchronizer:
    """Import channel uploads and conservatively link local backup files."""

    def __init__(self, settings: Settings, repository: UploadHistoryRepository) -> None:
        self.settings = settings
        self.repository = repository

    def _list_uploads(self, youtube: Any) -> list[dict[str, Any]]:
        channel_response = youtube.channels().list(
            part="contentDetails", mine=True
        ).execute()
        channels = channel_response.get("items", [])
        if not channels:
            raise RuntimeError("No YouTube channel was found for the authenticated account.")

        uploads_playlist_id = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        records = []
        page_token = None
        while True:
            response = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=page_token,
            ).execute()
            records.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return records

    @staticmethod
    def _file_hash(file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as video_file:
            for chunk in iter(lambda: video_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _local_files(self) -> list[Path]:
        if not self.settings.uploaded_dir.exists():
            return []
        return [
            file_path
            for file_path in self.settings.uploaded_dir.rglob("*")
            if file_path.is_file()
            and file_path.name.lower().endswith(self.settings.allowed_extensions)
        ]

    def sync(self, youtube: Any) -> int:
        youtube_items = self._list_uploads(youtube)
        local_files = self._local_files()
        local_by_title = {}
        for file_path in local_files:
            local_by_title.setdefault(file_path.stem, []).append(file_path)

        for item in youtube_items:
            snippet = item.get("snippet", {})
            video_id = item.get("contentDetails", {}).get("videoId")
            title = snippet.get("title", "")
            matching_files = local_by_title.get(title, [])
            local_file = matching_files[0] if len(matching_files) == 1 else None
            record = {
                "youtube_video_id": video_id,
                "title": title,
                "file_path": str(local_file) if local_file else None,
                "file_hash": self._file_hash(local_file) if local_file else None,
                "file_size": local_file.stat().st_size if local_file else None,
                "category": local_file.parent.name if local_file else None,
                "playlist_id": None,
                "uploaded_at": snippet.get("publishedAt"),
                "status": "uploaded",
                "source": "youtube_sync",
            }
            self.repository.upsert(record)

        LOGGER.info(
            "Synchronized %s YouTube uploads and linked %s local files.",
            len(youtube_items),
            sum(
                1
                for item in youtube_items
                if len(local_by_title.get(item.get("snippet", {}).get("title", ""), []))
                == 1
            ),
        )
        return len(youtube_items)
"""YouTube video upload service."""

from datetime import datetime, timezone
import hashlib
import logging
import mimetypes
import os
from pathlib import Path
import pickle
import random
import stat
import time
from typing import Any

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.history import UploadHistoryRepository
from src.settings import Settings


LOGGER = logging.getLogger(__name__)


class YouTubeUploader:
    """Upload local videos and apply the existing post-upload workflow."""

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]
    STOP_ERRORS = (
        "quotaExceeded",
        "exceeded your quota",
        "uploadLimitExceeded",
        "exceeded the number of videos they may upload",
    )
    RETRYABLE_STATUS_CODES = (408, 429, 500, 502, 503, 504)
    MAX_UPLOAD_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 5

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.history = UploadHistoryRepository(settings.history_db)

    def get_authenticated_service(self) -> Any:
        credentials = None

        if self.settings.token_file.exists():
            with self.settings.token_file.open("rb") as token:
                credentials = pickle.load(token)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    LOGGER.info("Token refreshed successfully")
                except Exception as error:
                    LOGGER.warning("Token refresh failed: %s", error)
                    LOGGER.warning(
                        "Deleting token.pickle and requesting new OAuth login..."
                    )
                    try:
                        self.settings.token_file.unlink()
                    except OSError:
                        pass
                    credentials = None
            else:
                LOGGER.info("No valid token found. Starting OAuth login...")

            if not credentials or not credentials.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.settings.credentials_file), self.SCOPES
                )
                credentials = flow.run_local_server(port=0)
                with self.settings.token_file.open("wb") as token:
                    pickle.dump(credentials, token)

        return build("youtube", "v3", credentials=credentials)

    def upload_video(
        self, youtube: Any, file_path: Path, playlist_id: str, category: str = "shorts"
    ) -> str:
        LOGGER.info("Uploading: %s to playlist (%s) ...", file_path, category)
        title = file_path.stem
        description = f"Uploaded via API to {category} playlist"

        request_body = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": "unlisted",
                "selfDeclaredMadeForKids": False,
            },
        }

        mime_type, _ = mimetypes.guess_type(str(file_path))
        media_file = MediaFileUpload(
            str(file_path),
            chunksize=-1,
            resumable=True,
            mimetype=(mime_type or "video/mp4"),
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media_file,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                LOGGER.info(
                    "Uploading %s: %s%%", file_path, int(status.progress() * 100)
                )

        video_id = response["id"]
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()

        LOGGER.info(
            "Uploaded %s (Video ID: %s) -> Playlist: %s",
            file_path,
            video_id,
            category,
        )
        return video_id

    def _find_videos(self) -> list[tuple[Path, str]]:
        videos_to_upload = []
        for category, folder in self.settings.video_dirs.items():
            folder.mkdir(parents=True, exist_ok=True)
            for file_path in folder.iterdir():
                if file_path.is_file() and file_path.name.lower().endswith(
                    self.settings.allowed_extensions
                ):
                    videos_to_upload.append((file_path, category))
        return videos_to_upload

    def _ask_cleanup_choice(self) -> bool:
        cleanup_choice = ""
        while cleanup_choice not in ("b", "d"):
            cleanup_choice = input(
                "After a successful upload, move files to backup or delete them? (b/d): "
            ).strip().lower()
        return cleanup_choice == "b"

    @staticmethod
    def _file_hash(file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as video_file:
            for chunk in iter(lambda: video_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _select_upload_scope(
        self, videos_to_upload: list[tuple[Path, str]]
    ) -> list[tuple[Path, str]]:
        while True:
            choice = input(
                "Upload all files or how many first files? (a or number): "
            ).strip().lower()
            if choice == "a":
                return videos_to_upload
            try:
                count = int(choice)
            except ValueError:
                print("Enter 'a' or a whole number.")
                continue
            if 1 <= count <= len(videos_to_upload):
                return videos_to_upload[:count]
            print(f"Enter 'a' or a number from 1 to {len(videos_to_upload)}.")

    @staticmethod
    def _remove_read_only(file_path: Path) -> None:
        """Allow cleanup of files carrying the Windows read-only attribute."""
        try:
            file_path.chmod(file_path.stat().st_mode | stat.S_IWRITE)
        except OSError:
            pass

    @classmethod
    def _is_retryable_error(cls, error: Exception) -> bool:
        status = getattr(getattr(error, "resp", None), "status", None)
        if status in cls.RETRYABLE_STATUS_CODES:
            return True
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True
        message = str(error).lower()
        return any(
            phrase in message
            for phrase in (
                "timed out",
                "timeout",
                "connection reset",
                "temporarily unavailable",
                "service unavailable",
            )
        )

    def _upload_with_retries(
        self,
        youtube: Any,
        file_path: Path,
        playlist_id: str,
        category: str,
    ) -> str:
        for attempt in range(1, self.MAX_UPLOAD_ATTEMPTS + 1):
            try:
                return self.upload_video(youtube, file_path, playlist_id, category)
            except Exception as error:
                if (
                    attempt == self.MAX_UPLOAD_ATTEMPTS
                    or not self._is_retryable_error(error)
                ):
                    raise
                LOGGER.warning(
                    "Temporary upload failure for %s (attempt %s/%s): %s. "
                    "Retrying in %s seconds...",
                    file_path.name,
                    attempt,
                    self.MAX_UPLOAD_ATTEMPTS,
                    error,
                    self.RETRY_DELAY_SECONDS,
                )
                time.sleep(self.RETRY_DELAY_SECONDS)

    @staticmethod
    def _print_upload_summary(
        successful: list[str], skipped: list[str], failed: list[str]
    ) -> None:
        print("\nUpload result summary:")
        print(f"  Successful: {len(successful)}")
        print(f"  Skipped duplicates: {len(skipped)}")
        print(f"  Failed: {len(failed)}")
        if failed:
            print("  Failed files:")
            for file_name in failed:
                print(f"    - {file_name}")

    def _existing_upload(self, file_path: Path) -> Any:
        file_hash = self._file_hash(file_path)
        existing_upload = self.history.find_successful_by_hash(file_hash)
        if not existing_upload:
            existing_upload = self.history.find_successful_by_title(file_path.stem)
        return existing_upload

    def _upload_status(self, file_path: Path) -> str:
        existing_upload = self._existing_upload(file_path)
        if existing_upload:
            video_id = existing_upload["youtube_video_id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            return f"duplicate (skip) - {video_url}"
        return "ready for upload"

    def _print_dry_run(
        self,
        videos_to_upload: list[tuple[Path, str]],
        move_to_backup: bool,
    ) -> None:
        cleanup_action = "move to uploaded/<category>" if move_to_backup else "delete"
        print("\nDry-run preview (no files will be changed):")
        for file_path, category in videos_to_upload:
            playlist_id = self.settings.playlist_id_for(category)
            status = self._upload_status(file_path)
            if status == "ready for upload":
                status += f" -> playlist {playlist_id}"
            print(f"  {file_path.name} [{category}] - {status}; cleanup: {cleanup_action}")
        print(f"\nWould process {len(videos_to_upload)} file(s).")

    def run(self, dry_run: bool = False) -> None:
        move_to_backup = self._ask_cleanup_choice()
        videos_to_upload = self._find_videos()

        if not videos_to_upload:
            LOGGER.info("No videos found for upload.")
            return

        print("\nUpload Summary:")
        for category in self.settings.video_dirs:
            category_videos = [
                file_path for file_path, video_category in videos_to_upload
                if video_category == category
            ]
            print(f"{category.capitalize()}: {len(category_videos)}")
            for file_path in category_videos:
                print(f"   - {file_path.name} - {self._upload_status(file_path)}")
        print(f"TOTAL: {len(videos_to_upload)} videos\n")

        videos_to_upload = self._select_upload_scope(videos_to_upload)
        print(f"Selected {len(videos_to_upload)} video(s) for upload.\n")

        if dry_run:
            self._print_dry_run(videos_to_upload, move_to_backup)
            return

        confirm = input("Start uploading? (y/n): ")
        if confirm.lower() != "y":
            print("Upload cancelled.")
            return

        file_hashes = {}
        new_videos = []
        skipped_files = []
        for file_path, category in videos_to_upload:
            existing_upload = self._existing_upload(file_path)
            if existing_upload:
                LOGGER.info(
                    "Skipping duplicate: %s (already uploaded as %s)",
                    file_path.name,
                    existing_upload["youtube_video_id"],
                )
                skipped_files.append(file_path.name)
                continue
            file_hash = self._file_hash(file_path)
            file_hashes[file_path] = file_hash
            new_videos.append((file_path, category))

        if not new_videos:
            LOGGER.info("All selected files have already been uploaded.")
            self._print_upload_summary([], skipped_files, [])
            return

        videos_to_upload = new_videos

        youtube = self.get_authenticated_service()
        self.settings.uploaded_dir.mkdir(parents=True, exist_ok=True)
        total_videos = len(videos_to_upload)
        successful_files = []
        failed_files = []

        for index, (file_path, category) in enumerate(videos_to_upload, start=1):
            playlist_id = self.settings.playlist_id_for(category)
            try:
                LOGGER.info(
                    "[%s/%s] Starting upload: %s",
                    index,
                    total_videos,
                    file_path.name,
                )
                video_id = self._upload_with_retries(
                    youtube, file_path, playlist_id, category
                )

                if move_to_backup:
                    destination = self.settings.uploaded_dir / category
                    destination.mkdir(parents=True, exist_ok=True)
                    self._remove_read_only(file_path)
                    os.rename(file_path, destination / file_path.name)
                    stored_path = destination / file_path.name
                    cleanup_message = "moved to backup"
                else:
                    self._remove_read_only(file_path)
                    file_path.unlink()
                    stored_path = None
                    cleanup_message = "deleted"

                self.history.upsert(
                    {
                        "youtube_video_id": video_id,
                        "title": file_path.stem,
                        "file_path": str(stored_path) if stored_path else None,
                        "file_hash": file_hashes[file_path],
                        "file_size": stored_path.stat().st_size if stored_path else None,
                        "category": category,
                        "playlist_id": playlist_id,
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                        "status": "uploaded",
                        "source": "upload",
                    }
                )

                LOGGER.info(
                    "[%s/%s] Completed: %s (%s)",
                    index,
                    total_videos,
                    file_path.name,
                    cleanup_message,
                )
                successful_files.append(file_path.name)
                time.sleep(random.randint(5, 15))
            except Exception as error:
                LOGGER.error(
                    "[%s/%s] Failed: %s: %s",
                    index,
                    total_videos,
                    file_path.name,
                    error,
                )
                failed_files.append(file_path.name)
                if any(stop_error in str(error) for stop_error in self.STOP_ERRORS):
                    LOGGER.error(
                        "Upload stopped after %s/%s successful uploads.",
                        index - 1,
                        total_videos,
                    )
                    break

                self._print_upload_summary(successful_files, skipped_files, failed_files)
"""Application settings loaded from the project and environment."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Paths and YouTube configuration shared by application services."""

    project_root: Path
    credentials_file: Path
    token_file: Path
    video_dirs: dict[str, Path]
    uploaded_dir: Path
    downloads_dir: Path
    history_db: Path
    phone_camera_videos_dir: Path
    playlists: dict[str, str]
    allowed_extensions: tuple[str, ...] = (
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".webm",
        ".m4v",
    )

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> "Settings":
        root = (project_root or Path(__file__).resolve().parent.parent).resolve()
        load_dotenv(root / ".env")
        phone_dcim = Path(
            os.getenv(
                "PHONE_DCIM_DIR",
                str(
                    Path.home()
                    / "CrossDevice"
                    / "Dipendra's S25 Ultra"
                    / "storage"
                    / "DCIM"
                ),
            )
        )

        return cls(
            project_root=root,
            credentials_file=root / "client_secrets.json",
            token_file=root / "token.pickle",
            video_dirs={
                "shorts": root / "videos" / "shorts",
                "landscape": root / "videos" / "landscape",
            },
            uploaded_dir=root / "uploaded",
            downloads_dir=root / "downloads",
            history_db=root / "data" / "upload_history.db",
            phone_camera_videos_dir=Path(
                os.getenv("PHONE_CAMERA_VIDEOS_DIR", str(phone_dcim / "Camera_Videos"))
            ),
            playlists={
                "shorts": os.getenv("YOUTUBE_SHORTS_PLAYLIST_ID", ""),
                "landscape": os.getenv("YOUTUBE_LANDSCAPE_PLAYLIST_ID", ""),
            },
        )

    def playlist_id_for(self, category: str) -> str:
        playlist_id = self.playlists.get(category, "")
        if not playlist_id:
            environment_name = f"YOUTUBE_{category.upper()}_PLAYLIST_ID"
            raise RuntimeError(
                f"Missing {environment_name}. Add it to your local .env file."
            )
        return playlist_id
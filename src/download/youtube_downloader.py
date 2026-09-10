"""YouTube video download service."""

from pathlib import Path
import shutil

import yt_dlp

from src.settings import Settings


class YouTubeDownloader:
    """Download a YouTube URL into the configured downloads directory."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def find_deno() -> str | None:
        deno_path = shutil.which("deno")
        if deno_path:
            return deno_path

        local_app_data = Path.home() / "AppData" / "Local"
        package_matches = local_app_data.glob(
            "Microsoft/WinGet/Packages/DenoLand.Deno_*/deno.exe"
        )
        return str(next(package_matches, "")) or None

    def download(self, url: str) -> None:
        self.settings.downloads_dir.mkdir(parents=True, exist_ok=True)
        options = {
            "outtmpl": str(self.settings.downloads_dir / "%(title)s.%(ext)s"),
        }
        deno_path = self.find_deno()
        if deno_path:
            options["js_runtimes"] = {"deno": {"path": deno_path}}
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([url])
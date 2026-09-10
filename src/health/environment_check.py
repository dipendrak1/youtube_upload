"""Check local prerequisites before using the application."""

from pathlib import Path
import shutil
import sys

import yt_dlp
from yt_dlp.version import __version__ as yt_dlp_version

from src.download import YouTubeDownloader
from src.settings import Settings


def _python_in_project_environment(settings: Settings) -> tuple[bool, Path]:
    executable_name = "python.exe" if sys.platform == "win32" else "python"
    expected_path = settings.project_root / ".venv" / (
        "Scripts" if sys.platform == "win32" else "bin"
    ) / executable_name
    try:
        active_path = Path(sys.executable).resolve()
        expected_path = expected_path.resolve()
    except OSError:
        return False, expected_path
    return active_path == expected_path, expected_path


def run_health_check(settings: Settings) -> bool:
    """Print local runtime checks and return whether required checks passed."""
    failures = 0
    warnings = 0

    def report(label: str, status: str, detail: str) -> None:
        nonlocal failures, warnings
        if status == "FAIL":
            failures += 1
        elif status == "WARN":
            warnings += 1
        print(f"[{status}] {label}: {detail}")

    print("Runtime health check")
    print("=" * 21)
    report("Python", "OK", sys.executable)

    venv_active, expected_python = _python_in_project_environment(settings)
    if venv_active:
        report("Virtual environment", "OK", str(expected_python))
    else:
        report(
            "Virtual environment",
            "WARN",
            f"active interpreter differs from {expected_python}",
        )

    report("yt-dlp", "OK", yt_dlp_version)

    deno_path = YouTubeDownloader.find_deno()
    if deno_path:
        report("Deno", "OK", deno_path)
    else:
        report("Deno", "FAIL", "not found on PATH or in the WinGet installation path")

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        report("FFmpeg", "OK", ffmpeg_path)
    else:
        report("FFmpeg", "FAIL", "not found on PATH")

    for category, folder in settings.video_dirs.items():
        status = "OK" if folder.exists() else "WARN"
        detail = str(folder) if folder.exists() else f"missing (created on upload): {folder}"
        report(f"Video folder ({category})", status, detail)

    if settings.downloads_dir.exists():
        report("Downloads folder", "OK", str(settings.downloads_dir))
    else:
        report(
            "Downloads folder",
            "WARN",
            f"missing (created on download): {settings.downloads_dir}",
        )

    if settings.credentials_file.exists():
        report("OAuth credentials", "OK", str(settings.credentials_file))
    else:
        report("OAuth credentials", "FAIL", f"missing: {settings.credentials_file}")

    if settings.token_file.exists():
        report("OAuth token", "OK", str(settings.token_file))
    else:
        report("OAuth token", "WARN", "not found (created during first OAuth login)")

    for category, playlist_id in settings.playlists.items():
        if playlist_id:
            report(f"Playlist ({category})", "OK", playlist_id)
        else:
            report(f"Playlist ({category})", "FAIL", "playlist ID is not configured")

    if settings.history_db.exists():
        report("History database", "OK", str(settings.history_db))
    else:
        report(
            "History database",
            "WARN",
            f"missing (created on first history operation): {settings.history_db}",
        )

    if failures:
        print(f"\nHealth check failed: {failures} required check(s) need attention.")
    elif warnings:
        print(f"\nHealth check passed with {warnings} advisory warning(s).")
    else:
        print("\nHealth check passed.")
    return failures == 0

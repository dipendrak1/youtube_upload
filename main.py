"""Single command-line entry point for the YouTube application."""

import argparse
import logging

from src.download import YouTubeDownloader
from src.history import UploadHistoryRepository, YouTubeHistorySynchronizer
from src.settings import Settings
from src.upload import YouTubeUploader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload or download YouTube videos.")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("upload", help="Upload videos from the configured folders.")

    download_parser = commands.add_parser(
        "download", help="Download a YouTube video."
    )
    download_parser.add_argument("url", help="YouTube URL to download.")

    commands.add_parser(
        "history-sync",
        help="Import YouTube uploads and local backups into SQLite history.",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    args = build_parser().parse_args()
    settings = Settings.from_project_root()

    if args.command == "upload":
        YouTubeUploader(settings).run()
    elif args.command == "download":
        YouTubeDownloader(settings).download(args.url)
    elif args.command == "history-sync":
        youtube = YouTubeUploader(settings).get_authenticated_service()
        repository = UploadHistoryRepository(settings.history_db)
        synchronizer = YouTubeHistorySynchronizer(settings, repository)
        synchronizer.sync(youtube)
        logging.info("Upload history contains %s records.", repository.count())


if __name__ == "__main__":
    main()
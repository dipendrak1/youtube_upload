"""Single command-line entry point for the YouTube application."""

import argparse
import logging

from src.download import YouTubeDownloader
from src.health import run_health_check
from src.history import UploadHistoryRepository, YouTubeHistorySynchronizer
from src.settings import Settings
from src.upload import YouTubeUploader


def print_history_report(report: dict) -> None:
    print("Upload history report")
    print("=" * 21)
    print(f"Total records: {report['total']}")

    for group_name in ("status", "category", "source"):
        print(f"\nBy {group_name}:")
        groups = report[group_name]
        if not groups:
            print("  (none)")
            continue
        for group in groups:
            name = group["name"] or "(uncategorized)"
            print(f"  {name}: {group['count']}")

    print("\nRecent records:")
    if not report["recent"]:
        print("  (none)")
        return
    for record in report["recent"]:
        uploaded_at = record["uploaded_at"] or "unknown date"
        video_id = record["youtube_video_id"] or "no video ID"
        category = record["category"] or "uncategorized"
        print(
            f"  {uploaded_at} | {record['title']} | {category} | "
            f"{record['status']} | {video_id}"
        )


def prompt_for_command() -> argparse.Namespace | None:
    def prompt_upload_mode() -> argparse.Namespace:
        while True:
            mode = input("Run a dry run or actual upload? (d/a): ").strip().lower()
            if mode == "d":
                return argparse.Namespace(command="upload", dry_run=True)
            if mode == "a":
                return argparse.Namespace(command="upload", dry_run=False)
            print("Enter 'd' for dry run or 'a' for actual upload.")

    while True:
        print("\nYouTube application")
        print("1. Upload videos")
        print("2. Download a video")
        print("3. Synchronize upload history")
        print("4. Show upload history report")
        print("5. Run runtime health check")
        print("q. Exit")
        choice = input("Choose an option: ").strip().lower()

        if choice == "1":
            return prompt_upload_mode()
        if choice == "2":
            url = input("Enter the YouTube URL: ").strip()
            if url:
                return argparse.Namespace(command="download", url=url)
            print("A YouTube URL is required.")
            continue
        if choice == "3":
            return argparse.Namespace(command="history-sync")
        if choice == "4":
            return argparse.Namespace(command="history-report", limit=10)
        if choice == "5":
            return argparse.Namespace(command="health-check")
        if choice == "q":
            return None
        print("Enter 1, 2, 3, 4, 5, or q.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload or download YouTube videos.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="global_dry_run",
        help="Preview the upload workflow when no command is supplied.",
    )
    commands = parser.add_subparsers(dest="command")

    upload_parser = commands.add_parser(
        "upload", help="Upload videos from the configured folders."
    )
    upload_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files and actions without authenticating or changing files.",
    )

    download_parser = commands.add_parser(
        "download", help="Download a YouTube video."
    )
    download_parser.add_argument("url", help="YouTube URL to download.")

    commands.add_parser(
        "history-sync",
        help="Import YouTube uploads and local backups into SQLite history.",
    )

    report_parser = commands.add_parser(
        "history-report",
        help="Show a local summary of upload history.",
    )
    report_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Number of recent records to show (default: 10).",
    )
    commands.add_parser(
        "health-check",
        help="Check local runtime prerequisites.",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    args = build_parser().parse_args()
    if args.command is None:
        if args.global_dry_run:
            args = argparse.Namespace(command="upload", dry_run=True)
        else:
            args = prompt_for_command()
    if args is None:
        return
    settings = Settings.from_project_root()

    if args.command == "health-check":
        if not run_health_check(settings):
            raise SystemExit(1)
    elif args.command == "upload":
        YouTubeUploader(settings).run(
            dry_run=getattr(args, "dry_run", False)
            or getattr(args, "global_dry_run", False)
        )
    elif args.command == "download":
        YouTubeDownloader(settings).download(args.url)
    elif args.command == "history-sync":
        youtube = YouTubeUploader(settings).get_authenticated_service()
        repository = UploadHistoryRepository(settings.history_db)
        synchronizer = YouTubeHistorySynchronizer(settings, repository)
        synchronizer.sync(youtube)
        logging.info("Upload history contains %s records.", repository.count())
    elif args.command == "history-report":
        if args.limit < 0:
            raise SystemExit("--limit must be zero or greater.")
        repository = UploadHistoryRepository(settings.history_db)
        print_history_report(repository.report(args.limit))


if __name__ == "__main__":
    main()
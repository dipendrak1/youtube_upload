# YouTube Upload and Download

This application uploads local videos to YouTube playlists and downloads YouTube videos through one command-line entry point.

## Project structure

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── src/
│   ├── settings.py
│   ├── upload/
│   │   └── youtube_uploader.py
│   └── download/
│       └── youtube_downloader.py
├── videos/
│   ├── shorts/
│   └── landscape/
├── uploaded/
└── downloads/
```
├── data/
│   └── upload_history.db

`Settings` owns paths and environment-backed configuration. `YouTubeUploader` owns OAuth, video uploads, playlist insertion, cleanup, and quota handling. `YouTubeDownloader` owns `yt-dlp` downloads. `main.py` orchestrates both services.

## Prerequisites

1. Install Python 3.11 or newer.
2. Enable YouTube Data API v3 in Google Cloud.
3. Create a Desktop OAuth client and place the downloaded file at `client_secrets.json` in the project root.
4. Create a local `.env` file from `.env.example` and set both playlist IDs:

```env
YOUTUBE_SHORTS_PLAYLIST_ID=your_shorts_playlist_id
YOUTUBE_LANDSCAPE_PLAYLIST_ID=your_landscape_playlist_id
```

Do not commit `client_secrets.json`, `token.pickle`, or `.env`.

The downloader also requires a JavaScript runtime for current YouTube
challenge solving. Install Deno on Windows with:

```powershell
winget install --id DenoLand.Deno --exact --scope user
```

## Upload history

The application stores upload history locally in SQLite at
`data/upload_history.db`. The database is ignored by Git and does not require
a separate database server.

To import existing uploads from the authenticated YouTube channel and link
local files already in `uploaded/`, run:

```powershell
python main.py history-sync
```

The sync records YouTube video IDs, titles, upload dates, statuses, and local
file metadata. A local file is linked only when its filename stem exactly
matches one unique YouTube title; uncertain matches are left unlinked rather
than guessed.

During normal uploads, each file is checked against successful history records
using its SHA-256 hash. Files already uploaded are skipped, even if their
filename has changed. New successful uploads are added to the database after
the YouTube upload and playlist insertion complete.

To view a local summary without authenticating with YouTube, run:

```powershell
python main.py history-report
```

The report shows totals grouped by status, category, and source, followed by
the 10 most recent records. Change the number of recent records with
`--limit`, or use `--limit 0` to show only the grouped totals:

```powershell
python main.py history-report --limit 25
```

## Setup

From the project root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On later sessions, activate the existing environment before running commands:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Upload videos

Place supported files (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, or `.m4v`) in `videos/shorts/` or `videos/landscape/`, then run:

```powershell
python main.py
```

Choose `Upload videos` from the menu, then choose `d` for a dry-run preview or
`a` for an actual upload. The existing command form,
`python main.py upload`, remains available for scripted use.

To preview the files, duplicate detection, playlists, and cleanup actions
without authenticating or changing any files, run:

```powershell
python main.py upload --dry-run
```

The application asks whether successfully uploaded files should be moved into `uploaded/<category>/` or deleted. It then shows a summary and asks for one upload scope choice: enter `a` for all detected files or a number for the first `N` files, followed by upload confirmation. The first upload opens the Google OAuth flow and stores the refreshed credentials in `token.pickle`.

Uploads retain the existing behavior: videos are unlisted, marked as not made for kids, categorized as People & Blogs, added to the configured playlist, and processing stops on YouTube quota or upload-limit errors. Temporary network failures are retried up to three times, and each batch ends with a summary of successful, skipped, and failed files.

## Download a video

Run `python main.py`, choose `Download a video`, and enter the YouTube URL.
Files are written to `downloads/` using the video title as the filename. The
existing command form is also supported:

```powershell
python main.py download "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Runtime health check

Run `python main.py`, choose `Run runtime health check`, or run the command
directly:

```powershell
python main.py health-check
```

The check verifies the active Python interpreter, virtual environment, yt-dlp,
Deno, FFmpeg, project folders, credentials, playlist IDs, and history database.
It reports advisories for optional first-run items and exits with an error when
required runtime items are missing.

## Validation

The application can be checked without making an API request with:

```powershell
python -m compileall -q main.py src
python main.py --help
```

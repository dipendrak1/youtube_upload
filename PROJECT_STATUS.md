# Project Status

## Current Stage

The project has a working command-line workflow for downloading, categorizing,
uploading, and synchronizing YouTube video history.

Implemented features include:

- Upload videos from `videos/shorts/` and `videos/landscape/`
- SHA-256 and title-based duplicate detection
- Dry-run upload previews, retries, and batch summaries
- YouTube OAuth authentication and playlist insertion
- `yt-dlp` video and playlist downloads
- SQLite upload history
- YouTube history synchronization and stale-record removal
- Runtime health checks
- Automatic categorization using FFmpeg metadata and rotation handling
- Excel upload-history export with hyperlinks, filters, and frozen headers
- Automatic Excel refresh after successful uploads

## Repository Checkpoint

- Branch: `main`
- Remote: `origin/main`
- Last known commit: `bc649eb Export upload history to Excel`
- Last known state: clean working tree, local branch aligned with `origin/main`

## Current Workflow

1. Download a single video URL without playlist parameters.
2. Move the downloaded file from `downloads/` into `videos/`.
3. Run `categorize` and confirm the preview.
4. Run `upload`.
5. Run `history-report` when an Excel report is needed.
6. Run `history-sync` when YouTube history needs reconciliation.

## Important Behavior

- Categorization scans only files directly inside `videos/`.
- Portrait and square videos become shorts; wider videos become landscape.
- Upload reads only `videos/shorts/` and `videos/landscape/`.
- Failed classification or destination collisions leave files unmoved.
- History synchronization does not modify local video files.
- Excel export failures do not mark an upload as failed.

## Project Commands

```powershell
.\.venv\Scripts\python.exe .\main.py categorize
.\.venv\Scripts\python.exe .\main.py upload
.\.venv\Scripts\python.exe .\main.py download "https://www.youtube.com/watch?v=VIDEO_ID"
.\.venv\Scripts\python.exe .\main.py history-report
.\.venv\Scripts\python.exe .\main.py history-sync
.\.venv\Scripts\python.exe -m compileall -q main.py src
git diff --check
git status --short --branch
```

## Constraints

- Do not commit or push unless explicitly requested.
- Keep `client_secrets.json`, `token.pickle`, `.env`, and `data/` private.
- Do not expose secrets or database contents in chat or documentation.
- Preserve stable upload behavior unless a requested change requires otherwise.
- Do not change local video files during history synchronization.

## Next Work

No feature is currently in progress. At the start of a new task, inspect this
file, the current Git status, and the relevant implementation or test surface.
Update this file when a meaningful feature, behavior, validation result, or
repository checkpoint changes.
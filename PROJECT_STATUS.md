# Project Status

## Current Stage

The project has a working command-line workflow for downloading, categorizing,
uploading, and synchronizing YouTube video history.

Implemented features include:

- Staged phone video import with file-by-file copy progress and verification
- Connected-phone trial copied and verified 3 of 12 files before interruption; 9 were not attempted, and phone originals remain in place
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
- Last known commit: `44fc91e Improve CLI menu prompts with numbered options`
- Last known state before phone-import work: clean working tree, local branch aligned with `origin/main`

## Current Workflow

1. Download a single video URL without playlist parameters.
2. Move the downloaded file from `downloads/` into `videos/`.
3. Optionally move phone videos into `Camera_Videos` manually, then choose `Import videos from phone` to copy supported files into project `videos/`.
4. Run `categorize` and confirm the preview.
5. Run `upload`.
6. Run `history-report` when an Excel report is needed.
7. Run `history-sync` when YouTube history needs reconciliation.

## Interactive Menu Updates

- The main CLI menu orders phone import, categorization, and upload as options `1-3`, followed by download, history sync, history report, and health check; it accepts `1-7` and `q` selections.
- Upload mode prompts now accept either `1/2` or `d/a` for dry-run vs. actual upload.
- Post-upload cleanup prompts now accept either `1/2` or `b/d` for backup vs. delete.
- Boolean confirmations now present numbered 1/2 choices such as “1. Yes / 2. No,” while older letter-based inputs remain supported for compatibility.

## Important Behavior

- Categorization scans only files directly inside `videos/`.
- Portrait and square videos become shorts; wider videos become landscape.
- Upload reads only `videos/shorts/` and `videos/landscape/`.
- Failed classification or destination collisions leave files unmoved.
- History synchronization does not modify local video files.
- Excel export failures do not mark an upload as failed.
- Phone import only copies from `Camera_Videos` into project `videos/`; it does not modify phone files.
- Phone import lets the user choose all files or the first N sorted files, lists the selected names with source/destination and size before confirmation, verifies copies with SHA-256, and never overwrites an existing destination.
- Phone import logs are written to `logs/phone_import.log`; phone paths can be overridden with `PHONE_DCIM_DIR` or `PHONE_CAMERA_VIDEOS_DIR`.

## Project Commands

```powershell
.\.venv\Scripts\python.exe .\main.py categorize
.\.venv\Scripts\python.exe .\main.py upload
.\.venv\Scripts\python.exe .\main.py download "https://www.youtube.com/watch?v=VIDEO_ID"
.\.venv\Scripts\python.exe .\main.py history-report
.\.venv\Scripts\python.exe .\main.py history-sync
.\.venv\Scripts\python.exe .\main.py phone-import
.\.venv\Scripts\python.exe -m compileall -q main.py src
.\.venv\Scripts\python.exe -m unittest tests.test_phone_video_importer -v
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

Phone video import is implemented as a copy-only operation and covered by
focused temporary-directory tests. Resume the connected-phone copy when ready;
existing project files are skipped and phone originals remain in place. Then
categorize and upload imported videos as desired. At the start of a new task, inspect this file, the current
Git status, and the relevant
implementation or test surface. Update this file when a meaningful feature,
behavior, validation result, or repository checkpoint changes.
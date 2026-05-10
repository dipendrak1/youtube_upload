# YouTube Uploader Automation

This project automates uploading videos to YouTube (Shorts & Landscape) using the YouTube Data API v3.

It can:
- Upload videos automatically
- Add videos to playlists
- Upload as **Unlisted**
- Mark videos as **Not Made for Kids**
- Move uploaded files into organized folders
- Stop automatically if YouTube API quota is exceeded

---

# 🔑 Prerequisites

## 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/?utm_source=chatgpt.com)
2. Create a new project (or use an existing one)
3. Enable **YouTube Data API v3**
4. Create **OAuth Client ID**
5. Select:
   - Application Type → **Desktop App**
6. Download the OAuth credentials JSON file
7. Rename it to:

```bash
client_secrets.json
```

---

# 📂 Project Structure

```text
project/
│
├── upload_folder.py
├── config.py
├── client_secrets.json
├── token.pickle
├── requirements.txt
│
├── videos/
│   ├── shorts/
│   └── landscape/
│
└── uploaded/
    ├── shorts/
    └── landscape/
```

---

# ⚙️ Setup

Place the `client_secrets.json` file in the project root folder.

Example:

```text
project/client_secrets.json
```

---

# 📦 Install Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

---

# 📄 Example requirements.txt

```text
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

---

# 🔑 First-Time Authentication

1. Run the uploader script once
2. Browser login window will open
3. Login with your Google/YouTube account
4. Grant YouTube permissions
5. After successful login:
   - `token.pickle` will be generated automatically
   - Future uploads will reuse this token

If the token expires, the script automatically refreshes it.

If refresh fails, the script deletes the old token and requests login again.

---

# ⚙️ Playlist Configuration

Update `config.py` with your actual playlist IDs.

Example:

```python
# config.py

PLAYLISTS = {
    "shorts": "YOUR_SHORTS_PLAYLIST_ID",
    "landscape": "YOUR_LANDSCAPE_PLAYLIST_ID",
}
```

Replace:
- `YOUR_SHORTS_PLAYLIST_ID`
- `YOUR_LANDSCAPE_PLAYLIST_ID`

with your actual YouTube playlist IDs.

You can find playlist IDs from playlist URLs:

```text
https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID
```

---

# 📹 Supported Video Formats

The uploader automatically detects and uploads these formats:

```text
.mp4
.mov
.mkv
.avi
.webm
.m4v
```

MIME type is detected automatically during upload.

---

# ▶️ Usage

## 1. Place Videos

Put videos inside:

```text
videos/shorts/
videos/landscape/
```

Example:

```text
videos/shorts/video1.mp4
videos/landscape/travel_vlog.mov
```

---

## 2. Run the Script

```bash
python upload_folder.py
```

---

# 📊 Upload Flow

The script will:

1. Scan all supported videos
2. Show upload summary
3. Ask for confirmation
4. Upload videos one by one
5. Add uploaded videos to playlists
6. Move uploaded videos to:
   - `uploaded/shorts/`
   - `uploaded/landscape/`

---

# 📝 Example Logs

```text
2026-05-08 19:46:11 [INFO] 🚀 [1/20] Starting upload: sample.mp4

2026-05-08 19:47:03 [INFO] ✅ [1/20] Completed: sample.mp4
```

---

# 🛑 Quota Handling

If YouTube API quota is exceeded, uploads stop immediately.

Example:

```text
2026-05-08 20:12:45 [ERROR] 🛑 YouTube API quota exceeded. Stopping further uploads.
```

This prevents unnecessary processing of remaining videos.

---

# 🔒 Upload Settings

Uploaded videos are automatically configured as:

- Privacy → **Unlisted**
- Audience → **Not Made for Kids**
- Category → **People & Blogs**

---

# 📌 Notes

- Do not share:
  - `client_secrets.json`
  - `token.pickle`

- Recommended `.gitignore`:

```gitignore
client_secrets.json
token.pickle
uploaded/
__pycache__/
```

---

# 🚀 Future Improvements (Optional)

Possible enhancements:
- Scheduled uploads
- Thumbnail uploads
- Automatic titles/descriptions
- Retry mechanism
- Multi-channel support
- Upload statistics
- GUI/Desktop app
- Docker support

---

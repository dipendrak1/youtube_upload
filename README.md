# YouTube Uploader Automation

This project automates uploading videos to YouTube (Shorts & Landscape) using the YouTube Data API v3.  
It organizes videos into playlists, sets privacy, and moves uploaded files into an `uploaded/` folder.

---

## 🔑 Prerequisites

1. **Create OAuth Credentials**  
   - Go to [Google Cloud Console](https://console.cloud.google.com/).  
   - Enable **YouTube Data API v3**.  
   - Create **OAuth Client ID (Desktop app)** credentials.  
   - Download the file and **rename it to**:  

   ```bash
   client_secrets.json
   ```


## 📂 Setup

Place the `client_secrets.json` file inside the project root folder (same directory as the script).

---

## 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

### Example `requirements.txt`

```
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

---

## 🔑 First-Time Authentication

1. Run the script once.  
2. A browser window will open for Google login & YouTube permissions.  
3. After successful authentication, a `token.json` file will be created for reuse.  

---

## ⚙️ Playlists Configuration

To automatically add uploaded videos to the right playlist, update the `config.py` file in the project root:

```json
{
  "playlists": {
    "shorts": "YOUR_SHORTS_PLAYLIST_ID",
    "landscape": "YOUR_LANDSCAPE_PLAYLIST_ID"
  }
}
```

👉 Replace `YOUR_SHORTS_PLAYLIST_ID` and `YOUR_LANDSCAPE_PLAYLIST_ID` with your actual YouTube playlist IDs.  
You can find the playlist ID in the YouTube playlist URL:  

```
https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID
```

---

## ▶️ Usage

1. Place your videos under:

```
videos/shorts/
videos/landscape/
```

2. Run the uploader script:

```bash
python upload_folder.py
```

3. The script will:
   - Summarize how many Shorts & Landscape videos are found  
   - Ask for confirmation before starting upload  
   - Upload videos as **Unlisted** and **Not Made for Kids**  
   - Add them to the correct playlist  
   - Move uploaded files to `videos/uploaded/`  


import os
import logging
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from config import PLAYLISTS
import mimetypes  # <-- ADDED

# --- CONFIG ---
# SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CREDENTIALS_FILE = "client_secrets.json"
TOKEN_FILE = "token.pickle"

# Video folders
VIDEO_DIRS = {
    "shorts": "videos/shorts",
    "landscape": "videos/landscape",
}

UPLOADED_DIR = "uploaded"

# Allowed video extensions (added)
ALLOWED_EXTS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v")

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# --- AUTH ---
def get_authenticated_service():
    creds = None

    # Load existing credentials if present
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # Case 1: No credentials or invalid → need new auth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                # Try refresh
                creds.refresh(Request())
                logging.info("🔄 Token refreshed successfully")
            except Exception as e:
                logging.warning(f"⚠ Token refresh failed: {e}")
                logging.warning("🗑 Deleting token.pickle and requesting new OAuth login...")

                # Delete token to force new login
                try:
                    os.remove(TOKEN_FILE)
                except:
                    pass
                creds = None  # force new flow
        else:
            logging.info("🔐 No valid token found. Starting OAuth login...")

        # If still no creds after refresh attempt → run OAuth flow
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

            # Save new token
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

# --- UPLOAD ---
def upload_video(youtube, file_path, playlist_id, category="shorts"):
    logging.info(f"Uploading: {file_path} to playlist ({category}) ...")
    title = os.path.splitext(os.path.basename(file_path))[0]
    description = f"Uploaded via API to {category} playlist"

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "unlisted",   # 🔥 Force Unlisted
            "selfDeclaredMadeForKids": False,  # 🔥 Mark as Not made for kids
        },
    }

    # determine mime type dynamically (changed)
    mime_type, _ = mimetypes.guess_type(file_path)
    media_file = MediaFileUpload(
        file_path,
        chunksize=-1,
        resumable=True,
        mimetype=(mime_type or "video/mp4"),  # fallback to video/mp4
    )  # 🔥 Explicit MIME

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logging.info(f"Uploading {file_path}: {int(status.progress() * 100)}%")

    video_id = response["id"]

    # Add to playlist
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()

    logging.info(f"✅ Uploaded {file_path} (Video ID: {video_id}) → Playlist: {category}")
    return video_id

# --- MAIN ---
def main():
    youtube = get_authenticated_service()

    videos_to_upload = []
    for category, folder in VIDEO_DIRS.items():
        os.makedirs(folder, exist_ok=True)
        for file in os.listdir(folder):
            # allow multiple video extensions (changed)
            if file.lower().endswith(ALLOWED_EXTS):
                videos_to_upload.append((os.path.join(folder, file), category))

    if not videos_to_upload:
        logging.info("No videos found for upload.")
        return

    print("\n📊 Upload Summary:")
    for cat in VIDEO_DIRS.keys():
        cat_videos = [f for f, c in videos_to_upload if c == cat]
        print(f"{cat.capitalize()}: {len(cat_videos)}")
        for v in cat_videos:
            print(f"   - {os.path.basename(v)}")
    print(f"TOTAL: {len(videos_to_upload)} videos\n")

    confirm = input("👉 Start uploading? (y/n): ")
    if confirm.lower() != "y":
        print("❌ Upload cancelled.")
        return

    os.makedirs(UPLOADED_DIR, exist_ok=True)

    for file_path, category in videos_to_upload:
        playlist_id = PLAYLISTS[category]
        try:
            upload_video(youtube, file_path, playlist_id, category)
            # Move uploaded file
            dest_folder = os.path.join(UPLOADED_DIR, category)
            os.makedirs(dest_folder, exist_ok=True)
            os.rename(file_path, os.path.join(dest_folder, os.path.basename(file_path)))
            time.sleep(2)  # Avoid quota issues
        except Exception as e:
            logging.error(f"❌ Failed to upload {file_path}: {e}")

if __name__ == "__main__":
    main()

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

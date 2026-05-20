import yt_dlp

url = "https://www.youtube.com/watch?v=VIDEO_ID"

ydl_opts = {
    'outtmpl': 'downloads/%(title)s.%(ext)s',
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
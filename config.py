import os

from dotenv import load_dotenv


load_dotenv()


def _required_playlist_id(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing {name}. Add it to your local .env file."
        )
    return value


PLAYLISTS = {
    "shorts": _required_playlist_id("YOUTUBE_SHORTS_PLAYLIST_ID"),
    "landscape": _required_playlist_id("YOUTUBE_LANDSCAPE_PLAYLIST_ID"),
}


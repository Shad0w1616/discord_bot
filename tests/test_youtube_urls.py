import sys
import unittest
from types import SimpleNamespace

sys.modules.setdefault("dotenv", SimpleNamespace(load_dotenv=lambda: None))
sys.modules.setdefault("yt_dlp", SimpleNamespace(YoutubeDL=object))

from music.youtube import YoutubeService


class YoutubeUrlTests(unittest.TestCase):
    def test_uses_regular_webpage_url(self) -> None:
        info = {"webpage_url": "https://www.youtube.com/watch?v=regular"}
        self.assertEqual(YoutubeService._get_webpage_url(info), info["webpage_url"])

    def test_builds_url_from_flat_video_id(self) -> None:
        info = {"id": "video-id", "url": "video-id", "_type": "url"}
        self.assertEqual(
            YoutubeService._get_webpage_url(info),
            "https://www.youtube.com/watch?v=video-id",
        )


class YoutubePlaylistTests(unittest.IsolatedAsyncioTestCase):
    async def test_accepts_flat_playlist_entries(self) -> None:
        service = object.__new__(YoutubeService)

        async def extract(query, playlist_limit=None):
            return {
                "title": "Playlist",
                "entries": [
                    {"id": "first", "url": "first", "title": "One"},
                    {"id": "second", "url": "second", "title": "Two"},
                ],
            }

        service.extract = extract
        playlist = await service.get_playlist("url", guild_id=1, max_items=2)

        self.assertEqual(playlist.count, 2)
        self.assertEqual(
            [track.url for track in playlist.tracks],
            [
                "https://www.youtube.com/watch?v=first",
                "https://www.youtube.com/watch?v=second",
            ],
        )

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from music.models import Track
from music.player import MusicPlayer
from music.wave import WaveSession
from music.youtube import YoutubeService


def track(index):
    return Track(str(index), f"https://www.youtube.com/watch?v={index:011d}", 1)


class MixTests(unittest.IsolatedAsyncioTestCase):
    async def test_mix_is_bounded_and_normalizes_flat_entries(self):
        service = object.__new__(YoutubeService)
        service.extract = AsyncMock(return_value={"entries": [
            {"id": "00000000001", "title": "First"}, None,
            {"url": "https://youtu.be/00000000002", "title": "Second"},
            {"id": "00000000003", "is_live": True},
            {"id": "00000000004", "availability": "private"},
        ]})
        result = await service.get_mix(track(1))
        self.assertEqual([t.url for t in result], [track(1).url, track(2).url])
        service.extract.assert_awaited_once_with(
            "https://www.youtube.com/watch?v=00000000001&list=RD00000000001",
            playlist_limit=50,
        )

    async def test_repeated_mix_terminates_without_duplicates(self):
        wave = WaveSession(track(1), 20)
        wave.add([track(1), track(1), track(2)])
        youtube = SimpleNamespace(get_mix=AsyncMock(return_value=[track(1), track(2)]))
        self.assertEqual((await wave.next_track(youtube)).url, track(1).url)
        self.assertEqual((await wave.next_track(youtube)).url, track(2).url)
        self.assertIsNone(await wave.next_track(youtube))
        self.assertLessEqual(youtube.get_mix.await_count, 3)

    async def test_new_batch_is_requested_only_after_pending_tracks(self):
        wave = WaveSession(track(1), 4)
        wave.add([track(1)])
        youtube = SimpleNamespace(get_mix=AsyncMock(return_value=[track(1), track(2)]))
        await wave.next_track(youtube)
        youtube.get_mix.assert_not_awaited()
        self.assertEqual((await wave.next_track(youtube)).url, track(2).url)
        youtube.get_mix.assert_awaited_once()
        wave.completed = 4
        self.assertIsNone(await wave.next_track(youtube))


class WavePlayerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.voice = Mock(guild=SimpleNamespace(id=1))
        self.voice.is_playing.return_value = False
        self.voice.is_paused.return_value = False
        self.voice.is_connected.return_value = True
        self.voice.disconnect = AsyncMock()
        self.voice.play.side_effect = lambda *a, **kw: setattr(self.voice.is_playing, "return_value", True)
        self.voice.stop.side_effect = lambda: setattr(self.voice.is_playing, "return_value", False)
        self.storage = SimpleNamespace(save=AsyncMock(), load=AsyncMock(return_value=[]))
        with patch("music.player.YoutubeService"):
            self.player = MusicPlayer(self.voice, SimpleNamespace(send=AsyncMock()),
                                      asyncio.get_running_loop(), self.storage)
        self.player.youtube = SimpleNamespace(
            get_track=AsyncMock(return_value=track(1)),
            get_mix=AsyncMock(return_value=[track(1), track(2), track(3), track(4)]),
            get_stream_url=AsyncMock(return_value="stream"),
            video_id=YoutubeService.video_id,
        )
        self.source_patch = patch("music.player.discord.FFmpegPCMAudio", return_value=Mock())
        self.source_patch.start()

    async def asyncTearDown(self):
        await self.player.shutdown()
        await asyncio.sleep(0)
        self.source_patch.stop()

    async def settle(self):
        for _ in range(8):
            await asyncio.sleep(0)

    async def finish(self, error=None):
        self.voice.is_playing.return_value = False
        await self.player.track_finished(error, self.player._epoch)
        await self.settle()

    async def test_exact_limit_includes_seed_and_wave_is_not_persisted(self):
        await self.player.start_wave("song", 2)
        await self.settle()
        self.assertEqual(self.player.current.url, track(1).url)
        self.storage.save.assert_not_awaited()
        await self.finish()
        self.assertEqual(self.player.current.url, track(2).url)
        await self.finish()
        self.assertFalse(self.player.wave_active)
        self.assertIsNone(self.player.current)
        self.assertEqual(self.voice.play.call_count, 2)

    async def test_skip_and_runtime_error_do_not_count(self):
        await self.player.start_wave("song", 2)
        await self.settle()
        await self.player.skip()
        await self.finish()
        self.assertEqual(self.player.wave.completed, 0)
        await self.finish(RuntimeError("audio failed"))
        self.assertEqual(self.player.wave.completed, 0)
        await self.finish()
        self.assertEqual(self.player.wave.completed, 1)

    async def test_failed_stream_is_replaced(self):
        self.player.youtube.get_stream_url.side_effect = [RuntimeError("unavailable"), "stream", "stream"]
        await self.player.start_wave("song", 1)
        await self.settle()
        self.assertEqual(self.player.current.url, track(2).url)
        self.assertEqual(self.player.wave.completed, 0)
        await self.finish()
        self.assertFalse(self.player.wave_active)

    async def test_stop_during_extraction_cannot_restart_audio(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def extract(url):
            entered.set()
            await release.wait()
            return "stream"

        self.player.youtube.get_stream_url.side_effect = extract
        await self.player.start_wave("song", 2)
        await entered.wait()
        await self.player.stop_wave()
        release.set()
        await self.settle()
        self.voice.play.assert_not_called()
        self.assertIsNone(self.player.current)

    async def test_stop_during_initial_mix_cancels_start(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def mix(seed):
            entered.set()
            await release.wait()
            return [track(2)]

        self.player.youtube.get_mix.side_effect = mix
        start = asyncio.create_task(self.player.start_wave("song", 2))
        await entered.wait()
        await self.player.stop_wave()
        release.set()
        with self.assertRaisesRegex(RuntimeError, "отменён"):
            await start
        self.assertFalse(self.player.wave_active)
        self.voice.play.assert_not_called()

    async def test_modes_are_exclusive_and_late_callback_is_ignored(self):
        await self.player.start_wave("song", 2)
        await self.settle()
        with self.assertRaises(RuntimeError):
            await self.player.enqueue(track(9))
        await self.player.set_repeat(True)
        self.assertTrue(self.player.repeat_enabled)
        epoch = self.player._epoch
        await self.player.stop_wave()
        await self.player.enqueue(track(9))
        await self.settle()
        await self.player.track_finished(epoch=epoch)
        self.assertEqual(self.player.current.url, track(9).url)
        with self.assertRaises(RuntimeError):
            await self.player.start_wave("song", 2)

    async def test_shutdown_does_not_restore_wave_as_normal_queue(self):
        await self.player.start_wave("song", 2)
        await self.settle()
        await self.player.shutdown(preserve_queue=True)
        self.storage.save.assert_awaited_with(1, [])

    async def test_ten_failures_end_wave_instead_of_retrying_forever(self):
        self.player.youtube.get_mix.return_value = [track(i) for i in range(1, 30)]
        self.player.youtube.get_stream_url.side_effect = RuntimeError("unavailable")
        with self.assertLogs("notorious", level="ERROR"):
            await self.player.start_wave("song", 20)
            for _ in range(30):
                await asyncio.sleep(0)
        self.assertFalse(self.player.wave_active)
        self.assertEqual(self.player.youtube.get_stream_url.await_count, 10)
        self.voice.play.assert_not_called()

    async def test_panel_is_automatic_and_old_buttons_are_disabled(self):
        await self.player.enqueue_many([track(1), track(2)])
        await self.settle()
        old_panel = self.player.panel_view
        self.assertIsNotNone(old_panel)
        self.assertTrue(old_panel.back.disabled)
        self.assertEqual(len(old_panel.to_components()), 3)
        await self.finish()
        self.assertFalse(old_panel.active)
        self.assertTrue(all(button.disabled for button in old_panel.children))
        self.assertIsNot(self.player.panel_view, old_panel)
        self.assertFalse(self.player.panel_view.back.disabled)

    async def test_previous_restores_order_and_ignores_stopped_callback(self):
        await self.player.enqueue_many([track(1), track(2), track(3)])
        await self.settle()
        await self.finish()
        epoch = self.player._epoch
        await self.player.previous()
        await self.settle()
        self.assertEqual(self.player.current.url, track(1).url)
        self.assertEqual([t.url for t in self.player.queue.all()], [track(2).url, track(3).url])
        await self.player.track_finished(epoch=epoch)
        self.assertEqual(self.player.current.url, track(1).url)

    async def test_wave_repeat_and_previous_do_not_double_count(self):
        await self.player.start_wave("song", 3)
        await self.settle()
        await self.player.set_repeat(True)
        await self.finish()
        self.assertEqual(self.player.current.url, track(1).url)
        self.assertEqual(self.player.wave.completed, 1)
        await self.finish()
        self.assertEqual(self.player.wave.completed, 1)
        await self.player.set_repeat(False)
        await self.finish()
        self.assertEqual(self.player.current.url, track(2).url)
        await self.player.previous()
        await self.settle()
        self.assertEqual(self.player.current.url, track(1).url)
        await self.finish()
        self.assertEqual(self.player.wave.completed, 1)
        self.assertEqual(self.player.current.url, track(2).url)

    async def test_shutdown_disables_panel_and_pause_updates_label(self):
        await self.player.enqueue(track(1))
        await self.settle()
        panel = self.player.panel_view
        self.voice.is_paused.return_value = True
        await self.player.refresh_panel()
        self.assertEqual(panel.pause.label, "Продолжить")
        await self.player.shutdown()
        self.assertFalse(panel.active)
        self.assertTrue(all(button.disabled for button in panel.children))

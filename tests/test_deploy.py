import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deploy import release


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sha = 'a' * 40
        self.folder = self.root / 'releases' / self.sha
        self.folder.mkdir(parents=True)
        for name in ['.env', 'cookies.txt']:
            (self.root / name).write_text('server-only')
        (self.folder / 'bot-image.tar.gz').write_bytes(b'image')
        (self.folder / 'bot-image.tar.gz.sha256').write_text(hashlib.sha256(b'image').hexdigest())
        self.previous = {
            'Image': 'old-id', 'Config': {'Labels': {'com.docker.compose.project': 'existing'}},
            'Mounts': [{'Destination': '/app/data', 'Type': 'volume', 'Name': 'old-data'},
                       {'Destination': '/tmp/yt-dlp', 'Type': 'volume', 'Name': 'old-cache'}],
        }

    def run_command(self, *args):
        if args[:3] == ('docker', 'image', 'inspect'):
            return json.dumps([{'Id': 'new-id', 'Config': {'Labels': {'org.opencontainers.image.revision': self.sha}}}])
        return ''

    def test_success_preserves_volumes_secrets_and_marks_revision(self):
        with patch.object(release, 'run', side_effect=self.run_command), patch.object(release, 'inspect_container', return_value=self.previous), patch.object(release, 'wait_healthy') as health:
            release.deploy(self.root, self.sha)
        health.assert_called_once_with('new-id')
        config = json.loads((self.folder / 'compose.json').read_text())
        self.assertEqual(config['volumes']['data']['name'], 'old-data')
        self.assertEqual(config['volumes']['cache']['name'], 'old-cache')
        self.assertTrue(config['volumes']['data']['external'])
        self.assertEqual((self.root / '.env').read_text(), 'server-only')
        self.assertEqual((self.root / 'deployed-revision').read_text().strip(), self.sha)
        self.assertFalse((self.folder / 'bot-image.tar.gz').exists())

    def test_unhealthy_release_rolls_back_and_does_not_mark_success(self):
        with patch.object(release, 'run', side_effect=self.run_command) as run, patch.object(release, 'inspect_container', return_value=self.previous), patch.object(release, 'wait_healthy', side_effect=[RuntimeError('unhealthy'), None]) as health:
            with self.assertRaises(RuntimeError):
                release.deploy(self.root, self.sha)
        self.assertEqual([c.args[0] for c in health.call_args_list], ['new-id', 'old-id'])
        run.assert_any_call('docker', 'tag', 'old-id', f'discord-bot:rollback-{self.sha}')
        self.assertFalse((self.root / 'deployed-revision').exists())

    def test_bad_checksum_never_replaces_container(self):
        (self.folder / 'bot-image.tar.gz').write_bytes(b'corrupt')
        with patch.object(release, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                release.deploy(self.root, self.sha)
        run.assert_called_once_with('docker', 'compose', 'version')

    def test_bind_mount_refused_instead_of_losing_data(self):
        self.previous['Mounts'][0]['Type'] = 'bind'
        with self.assertRaises(RuntimeError):
            release.volume_name(self.previous, '/app/data', 'default')

    def test_failed_first_release_is_stopped(self):
        with patch.object(release, 'run', side_effect=self.run_command) as run, patch.object(release, 'inspect_container', return_value=None), patch.object(release, 'wait_healthy', side_effect=RuntimeError('unhealthy')):
            with self.assertRaises(RuntimeError):
                release.deploy(self.root, self.sha)
        self.assertEqual(run.call_args.args[-1], 'stop')
        self.assertFalse((self.root / 'deployed-revision').exists())

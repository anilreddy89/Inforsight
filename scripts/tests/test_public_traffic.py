import importlib.util
import json
import hashlib
import tarfile
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('public_demo', Path(__file__).parents[1]/'public_demo.py')
public = importlib.util.module_from_spec(spec)
spec.loader.exec_module(public)


class StartupTests(unittest.TestCase):
    def test_upgrade_builds_only_missing_traffic_images(self):
        with tempfile.TemporaryDirectory() as directory:
            preview = public.Preview(Path(directory))
            preview.settings = {'project': 'inforsight-public-test', 'port': 3102}
            preview.compose = Mock()
            with patch.object(public, 'command', return_value=subprocess.CompletedProcess([], 1, '')):
                preview.ensure_traffic_images()
            self.assertEqual([call.args for call in preview.compose.call_args_list],
                             [('build', 'frontend'), ('build', 'traffic-dashboard')])
            self.assertEqual(preview.env()['INFORSIGHT_TRAFFIC_PORT'], '3113')
            self.assertEqual(preview.env()['COMPOSE_PROFILES'], 'traffic')
            self.assertEqual(len(preview.data_volumes()), 4)

    def test_current_images_reused_and_legacy_restores_remain_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            preview = public.Preview(Path(directory))
            preview.settings = {'project': 'inforsight-public-test', 'port': 3100}
            preview.compose = Mock()
            labels = {'com.inforsight.traffic.version': '2', 'com.inforsight.traffic.dashboard.version': '1'}
            result = subprocess.CompletedProcess([], 0, json.dumps([{'Config': {'Labels': labels}}]))
            with patch.object(public, 'command', return_value=result):
                preview.ensure_traffic_images()
            preview.compose.assert_not_called()
            services = {name: {'image': 'pinned'} for name in public.SERVICES if name != 'traffic-dashboard'}
            (Path(directory)/'restore-images.json').write_text(json.dumps({'services': services}))
            with patch.object(public, 'command') as command:
                preview.ensure_traffic_images()
            command.assert_not_called()
            self.assertEqual(preview.env()['COMPOSE_PROFILES'], '')
            self.assertEqual(preview.data_volumes(), ('postgres_data', 'kafka_data'))
            self.assertEqual(set(preview.services()), set(services))

    def test_restore_preserves_new_and_legacy_volume_sets(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source, state = root/'backup', root/'state'
                source.mkdir()
                (source/'secrets').mkdir()
                (state/'secrets').mkdir(parents=True)
                for name in ('db_password', 'demo_session_secret'):
                    (source/'secrets'/name).write_text('test-fixture-only')
                services = public.SERVICES[:-1] if legacy else public.SERVICES
                volumes = public.DATA_VOLUMES[:2] if legacy else public.DATA_VOLUMES
                manifest = {'components': [{'service': name, 'image_id': 'sha256:'+'a'*64} for name in services]}
                (source/'deployment-manifest.json').write_text(json.dumps(manifest))
                checksums = {}
                for volume in volumes:
                    path = source/(volume+'.tgz')
                    with tarfile.open(path, 'w:gz'):
                        pass
                    checksums[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                (source/'backup.json').write_text(json.dumps({'checksums': checksums}))
                preview = public.Preview(state)
                preview.settings = {'project': 'inforsight-public-test', 'port': 3102}
                def fake_command(args, **kwargs):
                    return subprocess.CompletedProcess(args, 1 if args[:3] == ['docker', 'volume', 'inspect'] else 0, '')
                with patch.object(public, 'command', side_effect=fake_command) as command:
                    preview.restore(source)
                restored = json.loads((state/'restore-images.json').read_text())
                self.assertEqual(set(restored['services']), set(services))
                self.assertEqual(preview.data_volumes(), volumes)
                creates = [call.args[0][-1] for call in command.call_args_list if call.args[0][:3] == ['docker', 'volume', 'create']]
                self.assertEqual(creates, ['inforsight-public-test_'+v for v in volumes])



if __name__ == '__main__':
    unittest.main()

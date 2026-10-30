import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from contracts.stage import ContractError
from harness import prototype


class PrototypeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict('os.environ', {'WORKSPACES_DIR': str(self.root), 'HOST_WORKSPACES_DIR': str(self.root), 'PROTOTYPE_ENABLED': '1', 'PROTOTYPE_PUBLIC_PATH': '/agent-prototype/'})
        self.env.start()
        self.runtime = self.root / '.prototype'
        self.runtime.mkdir()
        (self.runtime / 'compose.yaml').write_text('services: {}')

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_only_current_ready_run_has_a_link(self):
        prototype.claim('first')
        self.assertIsNone(prototype.url('first'))
        prototype.mark_ready('first')
        self.assertEqual(prototype.url('first'), '/agent-prototype/')
        prototype.claim('second')
        self.assertIsNone(prototype.url('first'))
        with self.assertRaises(ContractError):
            prototype.mark_ready('first')
        self.assertIsNone(prototype.url('second'))

    def test_deploy_copies_only_runtime_outputs_and_never_builds_images(self):
        product = self.root / 'run' / 'product'
        for folder, name in (('.publish/backend', 'App.Api.dll'), ('.publish/worker', 'App.Worker.dll'),
                             ('admin-web/dist/admin-web/browser', 'index.html'), ('mobile-web/dist/mobile-web/browser', 'index.html')):
            target = product / folder
            target.mkdir(parents=True)
            (target / name).write_text('compiled')
        (product / 'node_modules').mkdir()
        (product / 'node_modules' / 'not-runtime').touch()
        prototype.claim('run')
        commands = []
        def command(argv, **kwargs):
            commands.append(argv)
            return type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
        with patch('harness.prototype.subprocess.run', side_effect=command):
            prototype.deploy(product, 'run')
        self.assertTrue((self.runtime / 'current/backend/App.Api.dll').is_file())
        self.assertFalse((self.runtime / 'current/node_modules').exists())
        self.assertTrue(any('--no-build' in argv and '--wait' in argv for argv in commands))
        self.assertFalse(any('build' in argv for argv in commands))
        self.assertIsNone(prototype.url('run'))  # Smoke must confirm readiness separately.
        with patch.dict('os.environ', {'PROTOTYPE_PUBLIC_PATH': '/another-demo/'}), patch('harness.prototype.subprocess.run', side_effect=command):
            prototype.deploy(product, 'run')
        self.assertIn('^/another-demo/', (self.runtime / 'nginx.conf').read_text())
        self.assertIn('^/another-demo/mobile/', (self.runtime / 'mobile.conf').read_text())

    def test_reset_removes_only_prototype_and_failure_never_publishes(self):
        unrelated = self.root / 'other-run'
        unrelated.mkdir()
        (self.runtime / 'current').mkdir()
        (self.runtime / 'current/old.dll').touch()
        prototype.claim('run')
        with patch('harness.prototype.subprocess.run', return_value=type('Result', (), {'returncode': 1, 'stdout': '', 'stderr': 'runtime failed'})()):
            with self.assertRaises(ContractError):
                prototype.reset('run')
        self.assertIsNone(prototype.url('run'))
        self.assertTrue(unrelated.exists())

    def test_clean_demo_restarts_existing_artifacts_without_building(self):
        prototype.claim('run')
        current = self.runtime / 'current'
        current.mkdir()
        binary = current / 'kept.dll'
        binary.write_bytes(b'published')
        result = type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
        with patch('harness.prototype.subprocess.run', return_value=result) as command:
            prototype.reset_data('run')
        self.assertEqual(binary.read_bytes(), b'published')
        self.assertIn('-v', command.call_args_list[0].args[0])
        self.assertIn('--no-build', command.call_args_list[1].args[0])
        self.assertIsNone(prototype.url('run'))

    def test_public_path_rejects_external_or_unsafe_urls(self):
        for path in ('//evil.test/', 'https://evil.test/', '/bad/../path/', '/bad?x=1', '/'):
            with self.subTest(path=path), patch.dict('os.environ', {'PROTOTYPE_PUBLIC_PATH': path}):
                with self.assertRaises(ContractError):
                    prototype.public_path()


if __name__ == '__main__':
    unittest.main()

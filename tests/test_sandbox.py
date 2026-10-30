import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from contracts.stage import ContractError
from harness.sandbox import DockerSandbox


class SandboxTest(unittest.TestCase):
    def test_command_isolated_and_filter_is_literal(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"targets": {"backend": {"image": "tool:1", "test": ["dotnet", "test"], "filter": ["--filter", "AC={filter}"]}}}
            records = []
            sandbox = DockerSandbox(Path(tmp), "abc", config, record=lambda *x: records.append(x))
            with patch("harness.sandbox.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="ok", stderr="")) as invoke:
                result = sandbox.run("test", "backend", filter="AC-01")
            args = invoke.call_args.args[0]
            self.assertTrue(result.ok)
            self.assertIn("none", args)
            self.assertIn("AC=AC-01", args)
            self.assertIn("1000:1000", args)
            self.assertNotIn("OPENROUTER_API_KEY", invoke.call_args.kwargs["env"])
            self.assertEqual(len(records), 1)
            with self.assertRaises(ContractError):
                sandbox.run("test", "backend", filter="x;touch /tmp/pwned")

    def test_timeout_removes_container(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = DockerSandbox(Path(tmp), "abc", {"targets": {"backend": {"image": "tool", "build": ["build"]}}})
            with patch("harness.sandbox.subprocess.run", side_effect=[subprocess.TimeoutExpired("docker", 1), SimpleNamespace(returncode=0)]) as invoke:
                result = sandbox.run("build", "backend", timeout_s=1)
            self.assertEqual(result.exit_code, 124)
            self.assertEqual(invoke.call_args_list[1].args[0][:3], ["docker", "rm", "-f"])

    def test_junit_failure_or_invalid_report_cannot_pass(self):
        for xml in ('<testsuite><testcase name="a"><failure message="bad"/></testcase></testsuite>', '<not-xml'):
            with self.subTest(xml=xml), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'report.xml').write_text(xml)
                manifest = {'targets': {'backend': {'image': 'tool', 'test': ['test'], 'reports': {'junit': 'report.xml'}}}}
                sandbox = DockerSandbox(root, 'abc', manifest)
                with patch('harness.sandbox.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')):
                    result = sandbox.run('test', 'backend')
                self.assertFalse(result.ok)
                self.assertTrue(result.failed)

    def test_timeout_compose_up_tears_down_stack(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'compose.yml').write_text('services: {}')
            manifest = {'targets': {'stack': {'up': ['docker', 'compose', '-f', 'compose.yml', 'up', '-d']}}}
            sandbox = DockerSandbox(root, 'abc', manifest)
            with patch('harness.sandbox.subprocess.run', side_effect=[subprocess.TimeoutExpired('docker', 1), SimpleNamespace(returncode=0)]) as invoke:
                result = sandbox.run('up', 'stack', timeout_s=1)
            self.assertEqual(result.exit_code, 124)
            self.assertEqual(invoke.call_args_list[1].args[0], ['docker', 'compose', '-f', 'compose.yml', 'down', '-v'])
            self.assertEqual(invoke.call_args_list[1].kwargs['env']['COMPOSE_PROJECT_NAME'], 'run-abc')

    def test_rejects_privileged_and_host_binds(self):
        scenarios = [
            'services:\n  x:\n    image: x\n    privileged: true\n',
            'services:\n  x:\n    image: x\n    volumes: ["/var/run/docker.sock:/var/run/docker.sock"]\n',
            'services:\n  x:\n    image: x\n    network_mode: host\n',
            'services:\n  x:\n    image: x\n    volumes: ["${SOURCE}:/tmp"]\n',
        ]
        for content in scenarios:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'compose.yml').write_text(content)
                sandbox = DockerSandbox(root, 'abc', {'targets': {'stack': {'up': ['docker', 'compose', '-f', 'compose.yml', 'up']}}})
                with patch('harness.sandbox.subprocess.run') as invoke:
                    with self.assertRaises(ContractError):
                        sandbox.run('up', 'stack')
                    invoke.assert_not_called()

    def test_report_prefix_relative_to_run_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'result.xml').write_text('<testsuite/>')
            sandbox = DockerSandbox(root, 'abc', {'targets': {'backend': {'image': 'tool', 'test': ['test'], 'reports': {'junit': 'result.xml'}}}}, report_prefix='product')
            with patch('harness.sandbox.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')):
                self.assertEqual(sandbox.run('test', 'backend').reports['junit'], 'product/result.xml')

    def test_path_escape_and_missing_command_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = DockerSandbox(Path(tmp), "abc", {"targets": {"backend": {"image": "tool", "workdir": "../outside", "build": ["build"]}}})
            with self.assertRaises(ContractError):
                sandbox.run("build", "backend")
            with self.assertRaises(ContractError):
                sandbox.run("lint", "backend")


if __name__ == "__main__":
    unittest.main()

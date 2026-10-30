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
            owner = Path(tmp).stat()
            self.assertIn(f"{owner.st_uid}:{owner.st_gid}", args)
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
                manifest = {'targets': {'backend': {'image': 'tool', 'test': ['test'], 'reports': {'junit': 'report.xml'}}}}
                sandbox = DockerSandbox(root, 'abc', manifest)

                def writes_report(*args, xml=xml, **kwargs):
                    (root / 'report.xml').write_text(xml)
                    return SimpleNamespace(returncode=0, stdout='', stderr='')
                with patch('harness.sandbox.subprocess.run', side_effect=writes_report):
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
            sandbox = DockerSandbox(root, 'abc', {'targets': {'backend': {'image': 'tool', 'test': ['test'], 'reports': {'junit': 'result.xml'}}}}, report_prefix='product')

            def writes_report(*args, **kwargs):
                (root / 'result.xml').write_text('<testsuite/>')
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            with patch('harness.sandbox.subprocess.run', side_effect=writes_report):
                self.assertEqual(sandbox.run('test', 'backend').reports['junit'], 'product/result.xml')

    def test_path_escape_and_missing_command_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = DockerSandbox(Path(tmp), "abc", {"targets": {"backend": {"image": "tool", "workdir": "../outside", "build": ["build"]}}})
            with self.assertRaises(ContractError):
                sandbox.run("build", "backend")
            with self.assertRaises(ContractError):
                sandbox.run("lint", "backend")


    def test_restore_runs_once_with_network_then_build_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"targets": {"backend": {"image": "tool:1", "restore": ["dotnet", "restore"], "build": ["dotnet", "build", "--no-restore"],
                                              "env": {"NUGET_PACKAGES": "/work/.nuget/packages"}}}}
            sandbox = DockerSandbox(Path(tmp), "abc", config)
            ok = SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch("harness.sandbox.subprocess.run", return_value=ok) as invoke:
                sandbox.run("build", "backend")
                sandbox.run("build", "backend")
            calls = [call.args[0] for call in invoke.call_args_list]
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[0][calls[0].index("--network") + 1], "bridge")
            self.assertIn("restore", calls[0])
            self.assertTrue(all(call[call.index("--network") + 1] == "none" for call in calls[1:]))
            self.assertIn("NUGET_PACKAGES=/work/.nuget/packages", calls[1])

    def test_failed_restore_is_the_build_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"targets": {"admin": {"image": "tool:1", "restore": ["npm", "ci"], "build": ["npm", "run", "build"]}}}
            sandbox = DockerSandbox(Path(tmp), "abc", config)
            with patch("harness.sandbox.subprocess.run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="npm ERR! network")) as invoke:
                result = sandbox.run("build", "admin")
            self.assertFalse(result.ok)
            self.assertEqual(invoke.call_count, 1)

    def test_several_junit_files_are_merged_and_stale_ones_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "reports/junit/backend"
            folder.mkdir(parents=True)
            (folder / "Stale.xml").write_text('<testsuite><testcase name="old"><failure message="old"/></testcase></testsuite>')
            config = {"targets": {"backend": {"image": "tool:1", "test": ["dotnet", "test"], "reports": {"junit": "reports/junit/backend/*.xml"}}}}
            sandbox = DockerSandbox(root, "abc", config, report_prefix="product")

            def fake_run(argv, **kwargs):
                (folder / "App.Acceptance.Tests.xml").write_text('<testsuite><testcase name="a"/></testsuite>')
                (folder / "App.Generated.Tests.xml").write_text('<testsuites><testsuite><testcase name="b"/></testsuite></testsuites>')
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch("harness.sandbox.subprocess.run", side_effect=fake_run):
                result = sandbox.run("test", "backend")
            self.assertTrue(result.ok, result.failed)
            self.assertEqual(result.reports["junit"], "product/reports/junit-merged/backend.xml")
            import xml.etree.ElementTree as ET
            names = [case.get("name") for case in ET.parse(root / "reports/junit-merged/backend.xml").iter("testcase")]
            self.assertEqual(sorted(names), ["a", "b"])

    def test_compose_escaped_dollar_is_allowed_but_interpolation_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox = DockerSandbox(root, "abc", {})
            ok = root / "ok.yml"
            ok.write_text('services:\n  db:\n    image: postgis\n    healthcheck:\n      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]\n')
            sandbox._validate_compose(ok)
            bad = root / "bad.yml"
            bad.write_text('services:\n  db:\n    image: ${IMAGE}\n')
            with self.assertRaises(ContractError):
                sandbox._validate_compose(bad)


    def test_windows_host_path_from_docker_desktop_becomes_posix(self):
        from harness.sandbox import host_workspaces_dir
        with patch.dict("os.environ", {"HOST_WORKSPACES_DIR": r"C:\Users\dev\rwb\workspaces"}):
            path = host_workspaces_dir(Path("/app/workspaces"))
        self.assertEqual(path.as_posix(), "/c/Users/dev/rwb/workspaces")
        self.assertEqual((path / "local").resolve().as_posix(), "/c/Users/dev/rwb/workspaces/local")


    def test_product_template_passes_sandbox_validation(self):
        # The trusted template must be runnable as is: env keys, images and the stand compose file.
        import json
        import shutil
        template = Path(__file__).resolve().parents[1] / "templates" / "product"
        manifest = json.loads((template / "pack.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(template / "infra", root / "infra")
            for name in ("backend", "admin-web"):
                (root / name).mkdir()
                shutil.copy(template / name / "Dockerfile", root / name / "Dockerfile")
            sandbox = DockerSandbox(root, "abc", manifest)
            for target, config in manifest["targets"].items():
                if "image" in config:
                    sandbox._docker(config, ["true"], config.get("workdir", "."), "n", "none")
            sandbox._validate_compose(root / "infra" / "docker-compose.yml")


if __name__ == "__main__":
    unittest.main()

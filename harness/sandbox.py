"""Run trusted pack commands in resource-limited containers.

The manifest comes from the checked-in product template, never from model output.
The Docker daemon must see host_workspace at the same location as workspace.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

from contracts.stage import ContractError, SandboxKind, SandboxResult, SandboxTarget
from harness.fakes import workspace_path

_FILTER = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")
_RUN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_ENV = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}$")
_ERROR = re.compile(r"(?:\berror\b|\berror\s+\w+\s*:|\bFAIL(?:ED)?\b)", re.I)


class DockerSandbox:
    def __init__(self, workspace: Path, run_id: str, manifest: dict, *,
                 host_workspace: Path | None = None, report_prefix: str = "",
                 record: Callable[[str, str, SandboxResult], None] | None = None):
        self.workspace = Path(workspace).resolve()
        self.host_workspace = Path(host_workspace or workspace).resolve()
        self.manifest = manifest
        if report_prefix and (Path(report_prefix).is_absolute() or ".." in Path(report_prefix).parts):
            raise ContractError("Недопустимый префикс отчётов")
        self.report_prefix = report_prefix
        self.record = record
        run_id = str(run_id).lower()
        if not _RUN.fullmatch(run_id):
            raise ContractError("Недопустимый идентификатор прогона")
        self.project = f"run-{run_id}"
        self._restored: set[str] = set()

    def run(self, kind: SandboxKind, target: SandboxTarget, *,
            filter: str | None = None, timeout_s: int = 600) -> SandboxResult:
        if timeout_s <= 0:
            raise ContractError("Таймаут должен быть положительным")
        if filter is not None and not _FILTER.fullmatch(filter):
            raise ContractError("Недопустимый фильтр тестов")
        targets = self.manifest.get("targets", {})
        config = targets.get(target, {})
        if not isinstance(config, dict):
            raise ContractError("Некорректный манифест песочницы")
        scan = kind == "scan"
        if scan:
            scan_config = self.manifest.get("scan", {})
            commands = scan_config.get("commands", [])
            if not commands:
                raise ContractError("Команды сканирования отсутствуют")
            results = [self._execute(kind, target, scan_config, command, None, timeout_s) for command in commands]
            combined = SandboxResult(ok=all(r.ok for r in results), exit_code=next((r.exit_code for r in results if not r.ok), 0),
                duration_ms=sum(r.duration_ms for r in results), failed=[x for r in results for x in r.failed],
                output_tail="\n".join(r.output_tail for r in results)[-4000:], reports={k: v for r in results for k, v in r.reports.items()})
            if self.record:
                self.record(kind, target, combined)
            return combined
        if kind in ("up", "smoke", "down") and target != "stack":
            raise ContractError("Команда стенда доступна только для stack")
        if kind in ("build", "test", "e2e") and target not in self._restored and config.get("restore"):
            # Dependencies are fetched once with network access; build and tests then run offline.
            restored = self._execute("restore", target, config, config["restore"], None, timeout_s, network="bridge")
            if self.record:
                self.record("restore", target, restored)
            if not restored.ok:
                return restored
            self._restored.add(target)
        command = config.get(kind)
        result = self._execute(kind, target, config, command, filter, timeout_s)
        if self.record:
            self.record(kind, target, result)
        return result

    def _execute(self, kind: str, target: str, config: dict, command: object,
                 filter: str | None, timeout_s: int, network: str | None = None) -> SandboxResult:
        if not isinstance(command, list) or not command or not all(isinstance(v, str) and v for v in command):
            raise ContractError(f"Нет допустимой команды {kind}/{target} в pack.yaml")
        args = list(command)
        if filter is not None:
            template = config.get("filter")
            if not isinstance(template, list) or not all(isinstance(v, str) and v.count("{filter}") <= 1 for v in template) or not any("{filter}" in v for v in template):
                raise ContractError("В манифесте нет шаблона фильтра")
            args += [v.replace("{filter}", filter) for v in template]
        workdir = config.get("workdir", ".")
        if not isinstance(workdir, str):
            raise ContractError("Некорректный workdir")
        workspace_path(self.workspace, workdir)
        container_name = f"{self.project}-{uuid.uuid4().hex[:12]}"
        env = {key: os.environ[key] for key in ("PATH", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG", "HOME", "SSL_CERT_FILE") if key in os.environ}
        env["COMPOSE_PROJECT_NAME"] = self.project
        if target == "stack" and kind in ("up", "down", "smoke"):
            if kind in ("up", "down"):
                if args[:2] != ["docker", "compose"]:
                    raise ContractError("Команда стенда должна использовать docker compose")
                # Prevent reading arbitrary host files via a model-generated compose path.
                if "-f" not in args or args.index("-f") + 1 >= len(args):
                    raise ContractError("Не указан compose-файл")
                compose_file = workspace_path(self.workspace, args[args.index("-f") + 1])
                if kind == "up":
                    self._validate_compose(compose_file)
                argv = args
            else:
                # Smoke also runs in an isolated container, using the stack network.
                argv = self._docker(config, args, workdir, container_name, f"{self.project}_default")
        else:
            network = network or (f"{self.project}_default" if kind == "e2e" else "none")
            argv = self._docker(config, args, workdir, container_name, network)
        if kind in ("test", "e2e"):
            self._clear_reports(config)
        start = time.monotonic()
        try:
            completed = subprocess.run(argv, cwd=self.workspace, env=env, capture_output=True, text=True, errors="replace", timeout=timeout_s, check=False)
            output = completed.stdout + "\n" + completed.stderr
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            # Docker may keep daemon-side resources after its CLI is killed.
            try:
                if target == "stack" and kind == "up":
                    compose_file = args[args.index("-f") + 1]
                    subprocess.run(["docker", "compose", "-f", compose_file, "down", "-v"],
                                   cwd=self.workspace, env=env, capture_output=True, timeout=30, check=False)
                else:
                    subprocess.run(["docker", "rm", "-f", container_name], env=env, capture_output=True, timeout=15, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
            output = f"Превышен таймаут {timeout_s} с"
            exit_code = 124
        except OSError as exc:
            output = f"Не удалось запустить инструмент: {exc}"
            exit_code = 127
        elapsed = int((time.monotonic() - start) * 1000)
        failed = [line.strip() for line in output.splitlines() if _ERROR.search(line)][:100]
        report_failures: list[str] = []
        reports = self._reports(config, report_failures, target)
        failed.extend(report_failures)
        if report_failures and exit_code == 0:
            exit_code = 1
        if exit_code and not failed:
            failed.append(output.strip()[-1000:] or f"Код выхода: {exit_code}")
        return SandboxResult(ok=exit_code == 0, exit_code=exit_code, duration_ms=elapsed, failed=failed,
                             output_tail=output[-4000:], reports=reports)

    def _validate_compose(self, path: Path) -> None:
        """Fail closed on host access in the generated product's Compose file."""
        try:
            import yaml
            content = path.read_text(encoding="utf-8")
            # Interpolation can change a checked volume or privilege after validation.
            # "$$" is Compose's escaped literal dollar (e.g. in healthcheck commands).
            if "$" in content.replace("$$", ""):
                raise ContractError("Переменные в compose-файле не допускаются")
            data = yaml.safe_load(content)
        except (OSError, ImportError, ValueError) as exc:
            raise ContractError("Не удалось проверить compose-файл") from exc
        if not isinstance(data, dict) or not isinstance(data.get("services"), dict):
            raise ContractError("Некорректный compose-файл")
        if any(key in data for key in ("include", "configs", "secrets")):
            raise ContractError("Внешние compose-конфигурации запрещены")
        volumes = data.get("volumes") or {}
        if not isinstance(volumes, dict):
            raise ContractError("Некорректные тома")
        for config in volumes.values():
            if config and (not isinstance(config, dict) or config.get("external") or config.get("driver_opts") or config.get("driver")):
                raise ContractError("Внешние и настроенные тома запрещены")
        networks = data.get("networks") or {}
        if not isinstance(networks, dict) or any(v and (not isinstance(v, dict) or v.get("external") or v.get("driver_opts") or v.get("driver") not in (None, "bridge")) for v in networks.values()):
            raise ContractError("Внешние сети запрещены")
        denied = {"privileged", "devices", "device_cgroup_rules", "cap_add", "security_opt", "pid", "ipc", "network_mode", "userns_mode", "uts", "cgroup", "cgroup_parent", "sysctls", "runtime", "extends", "env_file", "secrets", "configs", "volumes_from", "use_api_socket", "extra_hosts", "dns", "dns_search", "dns_opt"}
        for service in data["services"].values():
            if not isinstance(service, dict) or any(key in service for key in denied):
                raise ContractError("Недопустимые настройки изоляции сервиса")
            for volume in service.get("volumes", []):
                if isinstance(volume, str):
                    parts = volume.split(":")
                    if len(parts) < 2:
                        continue
                    source = parts[0]
                    if not source or source not in volumes:
                        raise ContractError("Разрешены только именованные тома продукта")
                elif isinstance(volume, dict):
                    if volume.get("type") != "volume" or volume.get("source") not in volumes:
                        raise ContractError("Bind-монтирования запрещены")
                else:
                    raise ContractError("Некорректный том")
            build = service.get("build")
            if build:
                context = build if isinstance(build, str) else build.get("context", ".") if isinstance(build, dict) else None
                if not isinstance(context, str):
                    raise ContractError("Некорректный контекст сборки")
                try:
                    relative_context = str((path.parent / context).relative_to(self.workspace))
                except ValueError as exc:
                    raise ContractError("Контекст сборки вне продукта") from exc
                workspace_path(self.workspace, relative_context)
                if isinstance(build, dict):
                    if any(k in build for k in ("additional_contexts", "ssh", "secrets", "privileged", "entitlements")) or build.get("network", "none") != "none":
                        raise ContractError("Недопустимые настройки сборки")
                    dockerfile = build.get("dockerfile", "Dockerfile")
                    if not isinstance(dockerfile, str):
                        raise ContractError("Некорректный Dockerfile")
                    workspace_path(self.workspace, str(Path(relative_context) / dockerfile))

    def _docker(self, config: dict, args: list[str], workdir: str, name: str, network: str) -> list[str]:
        image = config.get("image")
        if not isinstance(image, str) or not image or image.startswith("-") or any(ch.isspace() for ch in image):
            raise ContractError("В манифесте не указан образ инструмента")
        env = config.get("env", {})
        if not isinstance(env, dict) or any(not isinstance(k, str) or not _ENV.fullmatch(k) or not isinstance(v, str) or "\n" in v
                                            for k, v in env.items()):
            raise ContractError("Некорректное окружение инструмента")
        # Run as the workspace owner: files the tool writes stay writable for the pipeline workers.
        owner = self.workspace.stat()
        return ["docker", "run", "--rm", "--name", name, "--network", network,
                "--cpus", "2", "--memory", "4g", "--user", f"{owner.st_uid}:{owner.st_gid}", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--mount", f"type=bind,src={self.host_workspace},dst=/work",
                *[item for key, value in sorted(env.items()) for item in ("-e", f"{key}={value}")],
                "--workdir", f"/work/{workdir}", image, *args]

    def _clear_reports(self, config: dict) -> None:
        """Stale JUnit files from an earlier run must not count as evidence for this one."""
        pattern = (config.get("reports") or {}).get("junit")
        if isinstance(pattern, str):
            workspace_path(self.workspace, pattern)
            for file in self.workspace.glob(pattern):
                if file.is_file():
                    file.unlink()

    def _reports(self, config: dict, failed: list[str], target: str = "") -> dict[str, str]:
        result = {}
        junit_files: list[Path] = []
        reports = config.get("reports", {})
        if not isinstance(reports, dict):
            raise ContractError("Некорректные пути отчётов")
        for kind, pattern in reports.items():
            if kind not in ("junit", "sarif", "coverage", "json") or not isinstance(pattern, str):
                raise ContractError("Некорректный тип отчёта")
            workspace_path(self.workspace, pattern)
            for file in sorted(self.workspace.glob(pattern)):
                relative = str(file.relative_to(self.workspace))
                workspace_path(self.workspace, relative)
                if not file.is_file():
                    continue
                result.setdefault(kind, str(Path(self.report_prefix) / relative))
                if kind == "junit":
                    junit_files.append(file)
                    try:
                        for case in ET.parse(file).iter("testcase"):
                            for issue in list(case):
                                if issue.tag in ("failure", "error"):
                                    failed.append(f"{case.get('classname', '')}::{case.get('name', '')}: {issue.get('message', '')}")
                    except ET.ParseError:
                        failed.append(f"Некорректный JUnit: {relative}")
        if len(junit_files) > 1:
            # One test assembly per file; consumers read a single report path, so merge them.
            merged = ET.Element("testsuites")
            for file in junit_files:
                try:
                    root = ET.parse(file).getroot()
                except ET.ParseError:
                    continue
                merged.extend(root if root.tag == "testsuites" else [root])
            relative = f"reports/junit-merged/{target or 'all'}.xml"
            path = workspace_path(self.workspace, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            ET.ElementTree(merged).write(path, encoding="utf-8", xml_declaration=True)
            result["junit"] = str(Path(self.report_prefix) / relative)
        return result


def host_workspaces_dir(container_dir: Path) -> Path:
    """Host path of the workspaces mount, needed for `docker run --mount` from inside a container.

    HOST_WORKSPACES_DIR wins; otherwise the worker inspects its own container mounts.
    """
    configured = os.environ.get("HOST_WORKSPACES_DIR")
    if configured:
        return Path(configured)
    container_dir = Path(container_dir).resolve()
    try:
        output = subprocess.run(["docker", "inspect", "--format", "{{json .Mounts}}", socket_hostname()],
                                capture_output=True, text=True, timeout=15, check=True).stdout
        import json
        for mount in json.loads(output) or []:
            if Path(mount.get("Destination", "")) == container_dir and mount.get("Source"):
                return Path(mount["Source"])
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    if not Path("/.dockerenv").exists():
        return container_dir  # running directly on the host
    raise ContractError("Не удалось определить путь workspaces на хосте: задайте HOST_WORKSPACES_DIR")


def socket_hostname() -> str:
    import socket
    return socket.gethostname()

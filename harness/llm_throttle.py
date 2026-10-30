"""One shared TPM/RPM/concurrency ledger for the workers on a single VPS."""
import hashlib
import io
import json
import math
import os
import time
import urllib.error
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from contracts.stage import ContractError


class AdmissionLimitExceeded(RuntimeError):
    pass


@dataclass
class Limiter:
    path: Path
    tpm: int
    rpm: int
    concurrent: int
    window: float
    safety: int
    bytes_per_token: float
    max_wait: float
    default_max_tokens: int = 4096

    @classmethod
    def from_env(cls):
        try:
            tpm = int(os.getenv('LLM_TPM_LIMIT', '0'))
            rpm = int(os.getenv('LLM_RPM_LIMIT', '0'))
            concurrent = int(os.getenv('LLM_MAX_PARALLEL', '1' if tpm or rpm else '0'))
            if min(tpm, rpm, concurrent) < 0:
                raise ValueError()
            if not (tpm or rpm or concurrent):
                return None
            limiter = cls(path=Path(os.getenv('LLM_RATE_LIMIT_FILE') or Path(os.getenv('WORKSPACES_DIR', 'workspaces')) / '.llm-rate-limit.json'),
                          tpm=tpm, rpm=rpm, concurrent=concurrent,
                          window=float(os.getenv('LLM_RATE_WINDOW_SECONDS', '60')),
                          safety=int(os.getenv('LLM_RATE_SAFETY_TOKENS', '512')),
                          bytes_per_token=float(os.getenv('LLM_RATE_INPUT_BYTES_PER_TOKEN', '3')),
                          max_wait=float(os.getenv('LLM_RATE_MAX_WAIT_SECONDS', '60')),
                          default_max_tokens=int(os.getenv('LLM_DEFAULT_MAX_TOKENS', '4096')))
            if limiter.default_max_tokens <= 0 or limiter.safety < 0 or any(not math.isfinite(value) or value <= 0 for value in (limiter.window, limiter.bytes_per_token, limiter.max_wait)):
                raise ValueError()
            return limiter
        except ValueError as exc:
            raise ContractError('Некорректные настройки лимитов LLM') from exc

    @contextmanager
    def ledger(self):
        # ponytail: native flock on one shared VPS disk; use a distributed store for multiple hosts.
        try:
            import fcntl
        except ImportError as exc:
            raise ContractError('Общий файловый лимитер LLM требует Linux или macOS') from exc
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with os.fdopen(os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600), 'r+') as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            raw = file.read()
            try:
                entries = json.loads(raw) if raw else []
                if not isinstance(entries, list) or any(not isinstance(entry, dict) or not all(key in entry for key in ('scope', 'id', 'start', 'end', 'tokens', 'pending', 'expires')) for entry in entries):
                    raise ValueError()
                for entry in entries:
                    if (not isinstance(entry['scope'], str) or not isinstance(entry['id'], str)
                            or type(entry['tokens']) is not int or entry['tokens'] < 0 or type(entry['pending']) is not bool
                            or any(type(entry[key]) not in (int, float) or not math.isfinite(entry[key]) for key in ('start', 'end', 'expires'))):
                        raise ValueError()
            except ValueError as exc:
                raise ContractError('Повреждён общий журнал лимитов LLM; восстановите его после остановки воркеров') from exc
            yield entries
            file.seek(0)
            json.dump(entries, file)
            file.truncate()
            file.flush()

    def reserve(self, scope, tokens, timeout, *, sleep=None, clock=None):
        if self.tpm and tokens + self.safety > self.tpm:
            raise ContractError('Один запрос к модели вместе с резервом ответа превышает лимит токенов в минуту. Уменьшите контекст или max_tokens.')
        sleep = sleep or time.sleep
        clock = clock or time.monotonic
        deadline = clock() + self.max_wait
        waited = 0
        while True:
            now = time.time()
            with self.ledger() as entries:
                entries[:] = [entry for entry in entries if max(entry['end'], entry['expires'] if entry['pending'] else 0) > now - self.window]
                scoped = [entry for entry in entries if entry['scope'] == scope]
                pending = [entry for entry in scoped if entry['pending'] and entry['expires'] > now]
                recent = [entry for entry in scoped if max(entry['end'], entry['expires'] if entry['pending'] else 0) > now - self.window]
                rpm_entries = [entry for entry in scoped if entry['start'] > now - self.window]
                fits = ((not self.tpm or sum(entry['tokens'] for entry in recent) + tokens + self.safety <= self.tpm)
                        and (not self.rpm or len(rpm_entries) < self.rpm)
                        and (not self.concurrent or len(pending) < self.concurrent))
                if fits:
                    ident = uuid.uuid4().hex
                    entries.append({'id': ident, 'scope': scope, 'start': now, 'end': now,
                                    'tokens': tokens, 'pending': True, 'expires': now + timeout + 5})
                    return ident
                expirations = [max(entry['end'], entry['expires'] if entry['pending'] else 0) + self.window for entry in recent]
                expirations += [entry['start'] + self.window for entry in rpm_entries]
                delay = min(1.0, max(0.01, min(expirations, default=now + 1) - now))
            remaining = min(deadline - clock(), self.max_wait - waited)
            if remaining <= 0:
                raise AdmissionLimitExceeded('Не удалось освободить общий лимит LLM за отведённое время. Прогон остановлен; повторите позже.')
            pause = min(delay, remaining)
            sleep(pause)
            waited += pause

    def finish(self, ident, actual_tokens=None):
        with self.ledger() as entries:
            for entry in entries:
                if entry['id'] == ident:
                    entry.update(pending=False, end=time.time(), expires=0)
                    if type(actual_tokens) is int and actual_tokens >= 0:
                        entry['tokens'] = actual_tokens
                    return


def open_throttled(opener, request, *, timeout, sleep=None, clock=None):
    limiter = Limiter.from_env()
    if limiter is None:
        return opener(request, timeout=timeout)
    try:
        payload = json.loads(request.data)
        output = payload.get('max_tokens', payload.get('max_completion_tokens'))
        if output is None:
            output = limiter.default_max_tokens
            payload['max_tokens'] = output
            request.data = json.dumps(payload).encode()
        if type(output) is not int or output <= 0 or payload.get('stream'):
            raise ValueError()
        prompt = {key: payload[key] for key in ('messages', 'tools', 'response_format') if key in payload}
        tokens = math.ceil(len(json.dumps(prompt, ensure_ascii=False).encode()) / limiter.bytes_per_token) + output
    except (ValueError, TypeError, AttributeError) as exc:
        raise ContractError('Лимитеру нужен JSON-запрос к модели с положительным max_tokens без stream') from exc
    endpoint = urlsplit(request.full_url)
    scope = hashlib.sha256((endpoint.scheme + endpoint.netloc + endpoint.path + request.get_header('Authorization', '')).encode()).hexdigest()
    clock = clock or time.monotonic
    started = clock()
    limiter.max_wait = min(limiter.max_wait, timeout)
    ident = limiter.reserve(scope, tokens, timeout, sleep=sleep, clock=clock)
    actual = None
    try:
        remaining = timeout - (clock() - started)
        if remaining <= 0:
            raise TimeoutError('Истёк срок ожидания запроса к модели')
        with opener(request, timeout=remaining) as response:
            body = response.read()
        usage = json.loads(body).get('usage') or {}
        if type(usage.get('total_tokens')) is int:
            actual = usage['total_tokens']
        elif type(usage.get('prompt_tokens')) is int and type(usage.get('completion_tokens')) is int:
            actual = usage['prompt_tokens'] + usage['completion_tokens']
        return io.BytesIO(body)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            actual = 0
        raise
    finally:
        limiter.finish(ident, actual)

"""Только eval: одноходовый OpenRouter/vLLM адаптер, пока нет шлюза Максима."""
from __future__ import annotations

import json
import os
import shlex
import time
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import BaseModel

from stages.analysis.compat import BudgetExceeded, ContractError, StageFailed


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().removeprefix("export ")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, raw = line.partition("=")
        lexer = shlex.shlex(raw, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = "#"
        values = list(lexer)
        if values:
            os.environ.setdefault(key.strip(), " ".join(values))


class EvalGateway:
    """Режимы генерации задаёт адаптер, а не стадии; истории сообщений нет."""
    def __init__(self, *, model: str = "qwen/qwen3.8-27b", base_url: str | None = None,
                 workspace: Path, max_tokens: int = 300000, max_calls: int = 120,
                 context_window: int = 32768) -> None:
        self.model = model
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        self.api_key = os.getenv("OPENROUTER_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.workspace = workspace
        self.max_tokens = max_tokens
        self.max_calls = max_calls
        self.context_window = context_window
        self.calls: list[dict] = []
        self.tokens_used = 0

    def __call__(self, *, task_class: str, system: str, user: str,
                 output: type[BaseModel] | str, task_id: str | None = None):
        if len(self.calls) >= self.max_calls or self.tokens_used >= self.max_tokens:
            raise BudgetExceeded("Исчерпан бюджет eval")
        if not isinstance(output, type) or not issubclass(output, BaseModel):
            raise ContractError("Этим стадиям нужен структурированный ответ модели")
        if "openrouter.ai" in self.base_url and not self.api_key:
            raise StageFailed("OPENROUTER_API_KEY не задан")
        original_schema = output.model_json_schema(by_alias=True)
        schema = dict(original_schema)
        definitions = schema.pop("$defs", {})
        transport = {"type": "object", "properties": {"result": schema}, "required": ["result"], "additionalProperties": False}
        if definitions:
            transport["$defs"] = definitions
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system + "\nOUTPUT_SCHEMA for the value under result:\n" + json.dumps(original_schema, ensure_ascii=False, separators=(",", ":")) + "\nTransport: return {\"result\": VALUE}. VALUE directly matches OUTPUT_SCHEMA; do not add a section-name wrapper."}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema", "json_schema": {"name": output.__name__, "strict": False, "schema": transport}},
            "max_tokens": min(8192, self.max_tokens - self.tokens_used),
            "temperature": 0.2,
            "reasoning": {"enabled": False},
        }
        if "openrouter.ai" in self.base_url:
            payload["provider"] = {"order": ["DeepInfra"], "allow_fallbacks": True, "require_parameters": True, "sort": "latency"}
        input_upper_bound = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()) + 256
        remaining_output = self.max_tokens - self.tokens_used - input_upper_bound
        remaining_output = min(remaining_output, self.context_window - input_upper_bound)
        if remaining_output < 64:
            raise BudgetExceeded("Бюджета или окна не хватает на входной контекст и ответ")
        payload["max_tokens"] = min(payload["max_tokens"], remaining_output)
        record = {"task_id": task_id, "task_class": task_class, "model": self.model,
                  "input_tokens": None, "output_tokens": None, "total_tokens": None,
                  "duration_ms": 0, "status": "started", "attempts": 0}
        self.calls.append(record)
        started = time.monotonic()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        try:
            body = None
            for attempt in range(2):
                record["attempts"] = attempt + 1
                request = urllib.request.Request(self.base_url + "/chat/completions", data=json.dumps(payload).encode(), headers=headers, method="POST")
                try:
                    with urllib.request.urlopen(request, timeout=120) as response:
                        body = json.load(response)
                    break
                except urllib.error.HTTPError as exc:
                    status = exc.code
                    exc.close()
                    if status in (429, 500, 502, 503, 504) and attempt == 0:
                        time.sleep(0.5)
                        continue
                    raise StageFailed(f"Провайдер модели вернул HTTP {status}") from None
                except (urllib.error.URLError, TimeoutError) as exc:
                    if attempt == 0:
                        continue
                    raise StageFailed("Не удалось дождаться провайдера модели") from None
            if body is None:
                raise StageFailed("Модель не вернула ответ")
            usage = body.get("usage", {})
            record.update(input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"), total_tokens=usage.get("total_tokens"))
            self.tokens_used += usage.get("total_tokens") or 0
            returned_model = body.get("model", self.model)
            record["returned_model"] = returned_model
            record["provider"] = body.get("provider")
            if returned_model.casefold() != self.model.casefold():
                raise StageFailed("Провайдер подменил запрошенную модель")
            choice = body["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ContractError("Модель исчерпала лимит ответа до завершения JSON")
            content = choice["message"].get("content")
            try:
                parsed = json.loads(content)
                result = output.model_validate(parsed["result"])
            except (ValueError, TypeError, KeyError) as exc:
                record["status"] = "contract_error"
                directory = self.workspace / "llm"
                directory.mkdir(parents=True, exist_ok=True)
                # Только выход модели и адреса ошибок; ключей здесь нет.
                (directory / f"{len(self.calls):03d}-invalid.json").write_text(json.dumps({"content": content, "schema": output.__name__}, ensure_ascii=False, indent=2))
                raise ContractError(f"Ответ модели нарушает схему {output.__name__}") from exc
            directory = self.workspace / "llm"
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{len(self.calls):03d}-result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
            record["status"] = "succeeded"
            return result
        except Exception as exc:
            if record["status"] == "started":
                record["status"] = "failed"
            record["error_type"] = type(exc).__name__
            raise
        finally:
            record["duration_ms"] = int((time.monotonic() - started) * 1000)

"""Bind the stage LLM protocol to durable per-request accounting."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app import tracing
from app.database import SessionLocal
from app.models import Event, LLMCall, Run
from harness.llm import Gateway, HTTPTransport, PROFILES, TASKS


def make_llm(run_id: UUID, stage_run_id: UUID, *, transport=None, tokenizer=None, attempt=1) -> Gateway:
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise LookupError('Прогон не найден')
        config = dict(run.config or {})
        cache_dir = Path(run.workspace_path).parent.parent / '.cache' / 'llm'

    client = transport or HTTPTransport()
    provider = getattr(client, 'provider', None) or 'openai-compatible'

    def start(meta):
        with SessionLocal.begin() as session:
            call = LLMCall(run_id=run_id, stage_run_id=stage_run_id, task_id=meta.get('task_id'),
                           task_class=meta['task_class'], provider=provider, model=meta['model'],
                           context_profile=meta['context_profile'], prompt_sha=meta.get('prompt_sha'), status='started',
                           from_cache=meta.get('from_cache', False))
            session.add(call)
            session.flush()
            return call.id

    def finish(call_id, values):
        with SessionLocal.begin() as session:
            call = session.get(LLMCall, call_id)
            if call is None:
                raise LookupError('Запись вызова модели не найдена')
            usage = values.get('usage') or {}
            call.tokens_in = usage.get('prompt_tokens')
            call.tokens_out = usage.get('completion_tokens')
            call.tokens_cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
            call.tokens_reasoning = (usage.get('completion_tokens_details') or {}).get('reasoning_tokens')
            call.status = values['status']
            call.from_cache = values.get('from_cache', call.from_cache)
            call.latency_ms = values.get('latency_ms')
            call.repair_rounds = values.get('repair_rounds', 0)
            call.ts_end = datetime.now(timezone.utc)
            session.add(Event(run_id=run_id, type='llm.call', payload={'id': str(call_id), 'status': call.status, 'from_cache': call.from_cache}))
            tracing.generation(call, values)

    def budget(exclude_unknown=()):
        with SessionLocal() as session:
            run = session.get(Run, run_id)
            if run is None:
                raise LookupError('Прогон не найден')
            calls = session.scalars(select(LLMCall).where(LLMCall.run_id == run_id, LLMCall.from_cache.is_(False))).all()
            # Reserve the maximum possible input/output for each unknown request;
            # recorded usage stays NULL and reports remain honest.
            used = 0
            for call in calls:
                if call.id in exclude_unknown and (call.tokens_in is None or call.tokens_out is None):
                    continue
                profile_limit = PROFILES.get(call.context_profile, PROFILES['M'])[0]
                policy = TASKS.get(call.task_class)
                output_limit = policy[1] + policy[3] if policy else 10000
                used += (call.tokens_in if call.tokens_in is not None else profile_limit)
                used += (call.tokens_out if call.tokens_out is not None else output_limit)
            elapsed = (datetime.now(timezone.utc) - (run.started_at or run.created_at)).total_seconds() / 60
            return used, run.tokens_limit, elapsed, run.minutes_limit

    def event(kind, payload):
        with SessionLocal.begin() as session:
            session.add(Event(run_id=run_id, type=kind, payload=payload))

    if tokenizer is None:
        import os
        tokenizer_path = os.getenv('LLM_TOKENIZER_PATH')
        if tokenizer_path:
            try:
                from tokenizers import Tokenizer
                model_tokenizer = Tokenizer.from_file(tokenizer_path)
                tokenizer = lambda value: len(model_tokenizer.encode(value).ids)
            except (ImportError, OSError, ValueError):
                event('llm.tokenizer_unavailable', {'method': 'chars/3'})

    return Gateway(start=start, finish=finish, budget=budget, event=event, transport=client,
                   profile=config.get('context_profile', 'M'), cache_dir=cache_dir, tokenizer=tokenizer, budget_excluding=budget,
                   structured=config.get('structured_output', True), cache_scope=f'{run_id}:{stage_run_id}' if attempt > 1 else '')

"""Mirror the run journal into Langfuse: run = trace, stage = span, model call = generation, gate = score.

Enabled only when LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set. A daemon thread sends
OTLP/HTTP JSON; an unavailable Langfuse logs a warning and never stops a run.
"""
import base64
import json
import logging
import os
import queue
import threading
import urllib.request

log = logging.getLogger(__name__)
_queue = queue.Queue(maxsize=2000)
_thread = None
_lock = threading.Lock()


def enabled():
    return all(os.getenv(name) for name in ('LANGFUSE_HOST', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY'))


def _post(path, body):
    auth = base64.b64encode(f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()).decode()
    request = urllib.request.Request(os.environ['LANGFUSE_HOST'].rstrip('/') + path, method='POST',
                                     data=json.dumps(body, ensure_ascii=False, default=str).encode(),
                                     headers={'Content-Type': 'application/json', 'Authorization': f'Basic {auth}',
                                              'x-langfuse-ingestion-version': '4'})
    urllib.request.urlopen(request, timeout=10).close()


def _drain():
    while True:
        path, body = _queue.get()
        try:
            _post(path, body)
        except Exception as exc:
            log.warning('Langfuse не принял наблюдение: %s', exc)


def _send(path, body):
    # shortcut: observations still queued when a short-lived process (CLI recover) exits are lost; add an atexit flush if that matters.
    global _thread
    with _lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_drain, name='langfuse', daemon=True)
            _thread.start()
    try:
        _queue.put_nowait((path, body))
    except queue.Full:
        log.warning('Очередь Langfuse переполнена, наблюдение пропущено')


def _value(value):
    if isinstance(value, bool):
        return {'boolValue': value}
    if isinstance(value, int):
        return {'intValue': str(value)}
    if isinstance(value, float):
        return {'doubleValue': value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return {'arrayValue': {'values': [{'stringValue': item} for item in value]}}
    return {'stringValue': value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)}


def span_body(run_id, span_id, parent_id, name, start, end, attributes, error=False):
    attributes = {'langfuse.trace.name': 'pipeline run', 'langfuse.trace.metadata.run_id': str(run_id), **attributes}
    span = {'traceId': run_id.hex, 'spanId': span_id, 'name': name, 'kind': 1,
            'startTimeUnixNano': str(int(start.timestamp() * 1e9)), 'endTimeUnixNano': str(int((end or start).timestamp() * 1e9)),
            'attributes': [{'key': key, 'value': _value(value)} for key, value in attributes.items() if value is not None],
            'status': {'code': 2 if error else 1}}
    if parent_id:
        span['parentSpanId'] = parent_id
    return {'resourceSpans': [{'resource': {'attributes': [{'key': 'service.name', 'value': {'stringValue': 'rwb-pipeline'}}]},
                               'scopeSpans': [{'scope': {'name': 'rwb-pipeline'}, 'spans': [span]}]}]}


def _span(*args, **kwargs):
    if enabled():
        _send('/api/public/otel/v1/traces', span_body(*args, **kwargs))


# Loops show up as WARNING attempts: a repair after schema_error, a regrow or continuation after length, a provider retry.
LEVELS = {'schema_error': 'WARNING', 'length': 'WARNING', 'provider_error': 'ERROR'}


def generation(call, values):
    status = 'length' if values.get('finish_reason') == 'length' else call.status
    usage = {key: value for key, value in (('input', call.tokens_in), ('output', call.tokens_out),
                                           ('reasoning', call.tokens_reasoning), ('cache_read', call.tokens_cached)) if value is not None}
    _span(call.run_id, call.id.hex[:16], call.stage_run_id.hex[:16], call.task_id or call.task_class, call.ts_start, call.ts_end, {
        'langfuse.observation.type': 'generation',
        'langfuse.observation.model.name': call.model,
        'langfuse.observation.input': values.get('messages'),
        'langfuse.observation.output': values.get('output'),
        'langfuse.observation.metadata.normalized_output': values.get('normalized_output'),
        'langfuse.observation.metadata.normalization': values.get('normalization'),
        'langfuse.observation.usage_details': usage or None,
        'langfuse.observation.model.parameters': {'max_tokens': values['max_tokens']} if values.get('max_tokens') else None,
        'langfuse.observation.level': LEVELS.get(status, 'DEFAULT'),
        'langfuse.observation.status_message': values.get('error') or (status if status in LEVELS else None),
        'langfuse.observation.metadata.status': status,
        'langfuse.observation.metadata.task_class': call.task_class,
        'langfuse.observation.metadata.repair_rounds': call.repair_rounds,
        'langfuse.observation.metadata.from_cache': call.from_cache,
        'langfuse.observation.metadata.context_profile': call.context_profile,
    }, error=status == 'provider_error')


def stage(row, gates):
    if not enabled():
        return
    failed = row.status == 'failed'
    _span(row.run_id, row.id.hex[:16], row.run_id.hex[:16], f'{row.stage} #{row.attempt}', row.started_at or row.created_at, row.finished_at, {
        'langfuse.observation.type': 'span',
        'langfuse.observation.level': 'ERROR' if failed else 'DEFAULT',
        'langfuse.observation.status_message': row.error,
        'langfuse.observation.output': row.summary,
        'langfuse.observation.metadata.status': row.status,
        'langfuse.observation.metadata.attempt': row.attempt,
    }, error=failed)
    for gate in gates:
        errors = sum(1 for finding in gate.findings or [] if finding.get('severity') == 'error')
        _send('/api/public/scores', {'traceId': row.run_id.hex, 'observationId': row.id.hex[:16], 'name': gate.gate,
                                     'value': 1 if gate.passed else 0, 'dataType': 'BOOLEAN',
                                     'comment': f'раунд {gate.round}, ошибок {errors}, решил {gate.decided_by}'})


def run(row):
    if not enabled():
        return
    _span(row.id, row.id.hex[:16], None, 'run', row.started_at or row.created_at, row.finished_at, {
        'langfuse.trace.metadata.project_id': str(row.project_id),
        'langfuse.trace.tags': [row.status, row.autonomy],
        'langfuse.session.id': str(row.project_id),
        'langfuse.observation.metadata.status': row.status,
    }, error=row.status == 'failed')


def normalization(run_id, stage_run_id, payload):
    from datetime import datetime, timezone
    from uuid import uuid4
    now = datetime.now(timezone.utc)
    _span(run_id, uuid4().hex[:16], stage_run_id.hex[:16], "normalization:" + (payload.get('task_id') or payload.get('source', 'response')), now, now, {
        'langfuse.observation.type': 'event',
        'langfuse.observation.input': payload.get('raw'),
        'langfuse.observation.output': payload.get('normalized'),
        'langfuse.observation.metadata.changes': payload.get('changes'),
        'langfuse.observation.metadata.normalization_version': payload.get('version'),
    })

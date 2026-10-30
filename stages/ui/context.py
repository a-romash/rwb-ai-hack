"""Compact, size-capped views of app.json, analysis.json and ui.json for one-shot prompts."""
import json
from typing import Any

from contracts.ui import UiSpec
from gates.g15_ui import reachable
from stages.ui.appview import AppView

MAX_PROMPT_CHARS = 24_000   # ~8k tokens of data; the gateway profile caps the rest
SEED_ROWS = 5


def dumps(data: Any, limit: int = MAX_PROMPT_CHARS) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= limit else text[:limit] + "…(обрезано)"


def app_brief(app: AppView, *, with_seed: bool = False) -> dict:
    brief: dict[str, Any] = {
        "lang": app.lang,
        "roles": {k: v.get("name", k) for k, v in app.roles.items()},
        "entities": {e: {"label": s.get("label", e),
                         "fields": {f: d.get("type") + (f":{d['ref']}" if d.get("ref") else "")
                                    for f, d in (s.get("fields") or {}).items()}}
                     for e, s in app.entities.items()},
        "commands": {c: {"entity": s.get("entity"), "roles": sorted(app.roles_for(c)),
                         "input": {k: v.get("type") for k, v in (s.get("input") or {}).items()}}
                     for c, s in app.commands.items()},
        "queries": {q: {"entity": s.get("entity"), "filter": s.get("filter"), "roles": s.get("roles")}
                    for q, s in app.queries.items()},
        "machines": {m: {"entity": s.get("entity"), "states": s.get("states"),
                         "transitions": [f"{t['name']}: {','.join(t.get('from', []))}->{t.get('to')}"
                                         f" by {next(iter(t.get('trigger') or {}), '?')}"
                                         for t in s.get("transitions") or []]}
                     for m, s in app.machines.items()},
        "events": sorted(app.events()),
        "hooks": {h: s.get("kind") for h, s in app.hooks.items()},
        "params": sorted(app.params),
    }
    if with_seed:
        brief["seed"] = {e: [{k: v for k, v in list(row.items())[:4]} for row in rows[:SEED_ROWS]]
                         for e, rows in app.seed.items()}
    return brief


def screens_brief(ui: UiSpec, names: list[str] | set[str]) -> dict:
    out = {}
    for name in sorted(names):
        s = ui.screens[name]
        out[name] = {
            "platform": s.platform, "pattern": s.pattern, "roles": s.roles, "title": s.title,
            "source": s.source.model_dump(exclude_none=True) if s.source else None,
            "widgets": [w.model_dump(exclude_none=True) for w in s.widgets],
            "actions": [a.model_dump(exclude_none=True, by_alias=True) for a in s.actions],
            "nav": s.nav,
        }
    return out


def walk_screens(ui: UiSpec, role: str, platform: str) -> dict:
    return screens_brief(ui, reachable(ui, role, platform))


def story(analysis: dict, us: str) -> dict:
    found = next((s for s in analysis.get("user_stories") or [] if s.get("id") == us), {})
    acs = [{"id": a["id"], "gherkin": (a.get("gherkin") or "")[:1200]}
           for a in analysis.get("acceptance") or [] if us in (a.get("stories") or []) and a.get("ui")]
    return {**found, "acceptance": acs}

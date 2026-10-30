"""Срезы анализа и компактные индексы готовых разделов спецификации."""
from __future__ import annotations

from contracts.analysis import Analysis


def empty_app(analysis: Analysis) -> dict:
    return {
        "schema_version": 1,
        "meta": {"name": "generated-app", "title": "Приложение", "lang": "ru-RU", "timezone": "Europe/Moscow", "modules": analysis.profile.modules},
        **{name: [] if name in ("permissions", "scenarios", "custom") else {} for name in ("params", "types", "entities", "roles", "permissions", "state_machines", "hooks", "commands", "queries", "events", "integrations", "schedules", "notifications", "seed", "scenarios", "custom")},
    }


def index(app: dict) -> dict:
    result: dict = {"meta": app["meta"]}
    for section in ("params", "types", "roles", "events", "integrations", "schedules", "notifications"):
        result[section] = list(app[section])
    result["entities"] = {name: {"fields": {field: {key: value for key, value in spec.items() if key in ("type", "ref", "machine", "computed_by", "required")} for field, spec in entity.get("fields", {}).items()}, "owner": entity.get("owner"), "traces": entity.get("traces", [])} for name, entity in app["entities"].items()}
    result["state_machines"] = {name: {"entity": machine["entity"], "states": machine["states"], "transitions": [{key: transition.get(key) for key in ("name", "from", "to", "trigger", "guard")} for transition in machine["transitions"]]} for name, machine in app["state_machines"].items()}
    result["hooks"] = {name: {key: hook.get(key) for key in ("kind", "in", "out", "rule")} for name, hook in app["hooks"].items()}
    result["commands"] = {name: {key: command.get(key) for key in ("entity", "roles", "traces")} for name, command in app["commands"].items()}
    result["queries"] = {name: {"entity": query["entity"], "roles": query["roles"]} for name, query in app["queries"].items()}
    result["permissions"] = app["permissions"]
    return result


def analysis_slice(analysis: Analysis, req_ids: set[str]) -> dict:
    stories = [story for story in analysis.user_stories if set(story.req) & req_ids]
    rules = [rule for rule in analysis.rules if set(rule.req) & req_ids]
    story_ids, rule_ids = {s.id for s in stories}, {r.id for r in rules}
    fields = {
        "requirements": [req for req in analysis.requirements if req.id in req_ids],
        "roles": analysis.roles, "glossary": analysis.glossary,
        "user_stories": stories, "rules": rules,
        "acceptance": [ac for ac in analysis.acceptance if set(ac.stories) & story_ids or set(ac.rules) & rule_ids],
        "assumptions": analysis.assumptions,
        "nfr": analysis.nfr,
    }
    return {key: [item.model_dump(mode="json", by_alias=True) for item in values] for key, values in fields.items()}

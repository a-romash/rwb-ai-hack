"""API scenarios of acceptance criteria, built from app.json without the model.

A criterion gets a scenario when app.json links it to an operation:
- a command traces the criterion, or a user story of the criterion whose role may run the command:
  create a record, move it with commands to a state the command accepts, run the command and check
  the status code and the new state;
- otherwise a role of the criterion's stories may create an entity that traces the story: create the
  record and read it back.
Timer transitions and notifications have no HTTP trigger and stay uncovered here.

File: cases/scenarios/<AC>.json, steps run by App.Acceptance.Tests/ScenarioCases.cs.
"""
import json
from collections import deque

from stages.scaffold.api import _body, _ops
from stages.ui.appview import derived_event

GENERATED = "product/backend/tests/App.Acceptance.Tests/Generated"
CASES = "product/backend/tests/App.Acceptance.Tests/cases/scenarios"


def _section(app: dict, key: str) -> dict:
    value = app.get(key)
    return value if isinstance(value, dict) else {}


def _story_roles(analysis: dict, ac: dict) -> dict[str, str]:
    stories = {us["id"]: us.get("role") for us in analysis.get("user_stories", [])}
    return {us: stories.get(us) for us in ac.get("stories", []) if us in stories}


def _state_field(app: dict, entity: str) -> tuple[str, dict] | None:
    for name, spec in ((_section(app, "entities").get(entity) or {}).get("fields") or {}).items():
        machine = _section(app, "state_machines").get(spec.get("machine"))
        if spec.get("type") == "state" and isinstance(machine, dict):
            return name, machine
    return None


def _moves(app: dict, entity: str, grants: set[str]) -> list[tuple[str, str, list[str], str, str]]:
    """(command, role, from states, to, transition) for command transitions of the entity's machine."""
    found = _state_field(app, entity)
    if not found:
        return []
    _, machine = found
    by_name = {t.get("name"): t for t in machine.get("transitions", [])}
    moves = []
    for command, spec in sorted(_section(app, "commands").items()):
        if spec.get("entity") != entity:
            continue
        role = next((r for r in sorted(spec.get("roles") or []) if f"{r}|{command}" in grants), None)
        role = role or next((g.split("|")[0] for g in sorted(grants) if g.endswith(f"|{command}")), None)
        if not role:
            continue
        for effect in spec.get("effects") or []:
            name = str(effect).rsplit(".", 1)[-1]
            transition = by_name.get(name)
            if transition and str(effect).startswith("transition:"):
                states = transition["from"] if isinstance(transition["from"], list) else [transition["from"]]
                moves.append((command, role, states, transition["to"], name))
    return moves


def _path(initial: str, targets: set[str], moves) -> list[tuple[str, str, str]] | None:
    """Shortest list of (command, role, to) leading from initial into one of targets."""
    queue, seen = deque([(initial, [])]), {initial}
    while queue:
        state, steps = queue.popleft()
        if state in targets:
            return steps
        for command, role, states, to, _ in moves:
            if state in states and to not in seen:
                seen.add(to)
                queue.append((to, steps + [(command, role, to)]))
    return None


def _creator(entity: str, grants: set[str], prefer: list[str]) -> str | None:
    for role in prefer + sorted(g.split("|")[0] for g in grants):
        if f"{role}|{entity}.create" in grants:
            return role
    return None


def _create_step(app: dict, entity: str, role: str) -> dict:
    body = _body((_section(app, "entities")[entity].get("fields") or {}), app)
    return {"as": role, "method": "POST", "path": f"/api/{entity}", "body": body,
            "expect": {"status": 201}, "save": "id"}


def _command_scenario(app: dict, ac: str, command: str, grants: set[str]) -> dict | None:
    spec = _section(app, "commands")[command]
    entity = spec.get("entity")
    found = _state_field(app, entity) if entity in _section(app, "entities") else None
    if not found:
        return None
    field, machine = found
    moves = _moves(app, entity, grants)
    targets = [m for m in moves if m[0] == command]
    creator = _creator(entity, grants, [])
    if not targets or not creator:
        return None
    for command_name, role, states, to, transition in targets:
        path = _path(machine.get("initial"), set(states), moves)
        if path is None:
            continue
        steps = [_create_step(app, entity, creator)]
        for step_command, step_role, step_to in path + [(command_name, role, to)]:
            body = {"id": "{id}", **_body(_section(app, "commands")[step_command].get("input") or {}, app)}
            steps.append({"as": step_role, "method": "POST", "path": f"/api/{entity}/commands/{step_command}",
                          "body": body, "expect": {"status": 200, "json": {field: step_to}}})
        # The transition is published to the outbox (R17): the event feed shows it for a reader.
        event = derived_event(entity, transition)
        reader = role if f"{role}|{entity}.read" in grants else next(
            (g.split("|")[0] for g in sorted(grants) if g.endswith(f"|{entity}.read")), None)
        if reader:
            steps.append({"as": reader, "method": "GET", "path": f"/api/{entity}/{{id}}", "body": None,
                          "expect": {"status": 200, "json": {field: to}}})
            steps.append({"as": reader, "method": "GET", "path": "/api/events", "body": None,
                          "expect": {"status": 200, "contains": {"type": event, "entity_id": "{id}"}}})
        return {"id": f"{ac}-{command}", "source": "command", "steps": steps}
    return None


def build(app: dict, analysis: dict) -> dict[str, list[dict]]:
    """AC id -> scenarios."""
    grants = _ops(app)
    result: dict[str, list[dict]] = {}
    for ac in analysis.get("acceptance", []):
        stories = _story_roles(analysis, ac)
        scenarios = []
        for command, spec in sorted(_section(app, "commands").items()):
            traces = set(spec.get("traces") or [])
            linked = ac["id"] in traces or any(us in traces and role in (spec.get("roles") or [])
                                               for us, role in stories.items())
            if linked:
                scenario = _command_scenario(app, ac["id"], command, grants)
                if scenario:
                    scenarios.append(scenario)
        if not scenarios:
            for entity, spec in sorted(_section(app, "entities").items()):
                traced = set(spec.get("traces") or []) & set(stories)
                role = next((stories[us] for us in sorted(traced) if f"{stories[us]}|{entity}.create" in grants), None)
                if role:
                    steps = [_create_step(app, entity, role)]
                    if f"{role}|{entity}.read" in grants:
                        steps.append({"as": role, "method": "GET", "path": f"/api/{entity}/{{id}}", "body": None,
                                      "expect": {"status": 200}})
                    scenarios.append({"id": f"{ac['id']}-create-{entity}", "source": "create", "steps": steps})
                    break
        if scenarios:
            result[ac["id"]] = scenarios
    return result


def write(workspace_path, root, ac: str, scenarios: list[dict]) -> list[str]:
    case = workspace_path(root, f"{CASES}/{ac}.json")
    case.parent.mkdir(parents=True, exist_ok=True)
    case.write_text(json.dumps({"schema_version": 1, "ac": ac, "scenarios": scenarios}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    ident = ac.replace("-", "_")
    source = workspace_path(root, f"{GENERATED}/{ident}_Scenario.cs")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "using Xunit;\n\n"
        "namespace App.Acceptance.Tests.Generated;\n\n"
        f"public sealed class {ident}_Scenario_Tests\n"
        "{\n"
        f"    public static TheoryData<string> Cases => ScenarioCases.For(\"{ac}\");\n\n"
        f"    [Theory, Trait(\"AC\", \"{ac}\"), MemberData(nameof(Cases))]\n"
        f"    public Task {ident}_Scenario(string key) => ScenarioCases.Run(key);\n"
        "}\n", encoding="utf-8")
    return [str(case.relative_to(root)), str(source.relative_to(root))]


__all__ = ["build", "write"]

"""Hook cases as JSON: examples of acceptance criteria -> hook inputs and expected result.

Rows of Gherkin `Examples` tables are extracted by code. When every hook input matches a column,
the row becomes a case without the model. Otherwise one structured call per hook maps the rows to
inputs (the model only translates values, it never invents the rows of a table). Rules with fewer
than three examples get boundary cases (N-1 / N / N+1) from the same call.
"""
import json
import re

from pydantic import BaseModel, Field, JsonValue

from contracts.stage import BudgetExceeded, ContractError

MIN_CASES = 3
CASES = "product/backend/tests/App.Acceptance.Tests/cases/hooks"
EXPECTED_HEADERS = {"expected", "result", "ожидается", "результат", "итог"}
TRUE_WORDS = {"да", "true", "yes", "истина"}
FALSE_WORDS = {"нет", "false", "no", "ложь"}


class Case(BaseModel):
    id: str
    ac: str
    inputs: dict[str, JsonValue]
    expected: JsonValue


class ModelCases(BaseModel):
    """What the model returns for one hook."""
    cases: list[Case] = Field(default_factory=list)


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]", "", str(text).lower())


def examples(gherkin: str) -> list[dict[str, str]]:
    """Rows of all Examples tables of the criterion, as header -> cell text."""
    from stages.spec.semantics import parse_gherkin, scenarios
    document = parse_gherkin(gherkin or "")
    if not document:
        return []
    rows = []
    for scenario in scenarios(document):
        for table in scenario.get("examples", []):
            header = [cell["value"] for cell in (table.get("tableHeader") or {}).get("cells", [])]
            for body in table.get("tableBody", []):
                values = [cell["value"] for cell in body.get("cells", [])]
                if len(values) == len(header):
                    rows.append(dict(zip(header, values)))
    return rows


def _value(text: str) -> JsonValue:
    word = text.strip()
    if word.lower() in TRUE_WORDS:
        return True
    if word.lower() in FALSE_WORDS:
        return False
    try:
        return json.loads(word)
    except ValueError:
        return word


def direct(hook: dict, ac: str, rows: list[dict[str, str]]) -> list[Case] | None:
    """Cases without the model: every input parameter and the expected value have a column."""
    inputs = [p for p in hook.get("parameters", []) if p["source"] == "input"]
    if not rows or not inputs:
        return None
    columns = {_norm(name): name for name in rows[0]}
    expected = next((name for key, name in columns.items() if key in {_norm(h) for h in EXPECTED_HEADERS}), None)
    mapped = {p["name"]: columns.get(_norm(p["name"])) for p in inputs}
    if expected is None or any(column is None for column in mapped.values()):
        return None
    return [Case(id=f"{ac}-{index}", ac=ac, inputs={name: _value(row[column]) for name, column in mapped.items()},
                 expected=_value(row[expected]))
            for index, row in enumerate(rows, 1)]


def related(hook: dict, analysis: dict) -> list[dict]:
    """Criteria the hook implements: its AC refs and criteria of its business rules."""
    refs = set(hook.get("refs", []))
    return [ac for ac in analysis.get("acceptance", [])
            if ac["id"] in refs or refs & set(ac.get("rules", []))]


def _types(hook: dict, app: dict) -> dict:
    """Shapes of the input types, so the model writes inputs the C# runner can deserialize."""
    entities, commands, types = (app.get(key) or {} for key in ("entities", "commands", "types"))
    shapes = {}
    for parameter in hook.get("parameters", []):
        name = parameter["type"].rstrip("?")
        source = entities.get(name) or commands.get(name)
        if source:
            fields = source.get("fields") or source.get("input") or {}
            shape = {field: spec.get("type") for field, spec in fields.items()}
            if name in commands and source.get("entity"):
                shape = {"id": "uuid", **shape}
            shapes[name] = shape
    shapes["enums"] = {name: spec.get("values", []) for name, spec in types.items()}
    machines = app.get("state_machines") or {}
    shapes["states"] = {name: machine.get("states", []) for name, machine in machines.items()}
    return shapes


SYSTEM = """You convert acceptance criteria examples into test cases for one pure function (a hook).
Return JSON only. For every example row given, return exactly one case with the same id and ac.
If the rule has fewer than three examples, add boundary cases (threshold minus one step, exactly the
threshold, plus one step) with ids "<ac>-extra-<n>".
inputs: one key per input parameter of the hook, using the exact parameter names given.
Objects use the field names of the given shapes (snake_case); enum and state values exactly as listed;
dates and times as ISO 8601 with offset (meta.timezone); durations as "hh:mm:ss"; ids as UUID strings.
expected: the value the function must return for that row, derived from the criterion, of the given
return type (bool for validators and policies). Never compute expected values from an implementation."""


def ask(llm, hook: dict, app: dict, analysis: dict, criteria: list[dict], rows: dict[str, list],
        rejected: dict | None = None) -> list[Case]:
    rules = {rule["id"]: rule for rule in analysis.get("rules", [])}
    packet = {
        "hook": {key: hook.get(key) for key in ("id", "kind", "method", "returns", "contract")},
        "input_parameters": [p for p in hook.get("parameters", []) if p["source"] == "input"],
        "shapes": _types(hook, app),
        "meta": app.get("meta", {}),
        "params": {name: spec.get("value") for name, spec in (app.get("params") or {}).items()},
        "rules": [rules[ref] for ref in hook.get("refs", []) if ref in rules],
        "criteria": [{"id": ac["id"], "gherkin": ac.get("gherkin", "")} for ac in criteria],
        "rows": [{"id": f"{ac}-{index}", "ac": ac, "values": row}
                 for ac, table in rows.items() for index, row in enumerate(table, 1)],
    }
    if rejected:
        # G2 repair: a new prompt, so the cache cannot hand back the cases that were just rejected.
        packet["previous_cases_rejected"] = rejected
    answer = llm(task_class="qa", system=SYSTEM, user=json.dumps(packet, ensure_ascii=False),
                 output=ModelCases, task_id=hook["id"])
    return answer.cases


def contradictions(cases: list[dict]) -> list[str]:
    """Pairs of cases with equal inputs and different expectations: no hook body passes both."""
    seen, found = {}, []
    for case in cases:
        key = json.dumps(case.get("inputs"), sort_keys=True, ensure_ascii=False)
        first = seen.setdefault(key, case)
        if first.get("expected") != case.get("expected"):
            found.append((case.get("ac"), f"кейсы {first.get('id')} и {case.get('id')}: одинаковые входы, разные ожидания "
                                          f"({first.get('expected')!r} и {case.get('expected')!r})"))
    return found


def check(hook: dict, cases: list[Case], wanted: set[str], criteria: set[str]) -> list[Case]:
    """Keep only well-formed cases; every extracted row must be present."""
    names = {p["name"] for p in hook.get("parameters", []) if p["source"] == "input"}
    good = [case for case in cases if case.ac in criteria and set(case.inputs) == names and case.expected is not None]
    missing = wanted - {case.id for case in good}
    if missing:
        raise ContractError(f"Хук {hook['id']}: нет кейсов для строк {sorted(missing)}")
    return good


def build(hook: dict, app: dict, analysis: dict, llm, feedback: dict[str, list[str]] | None = None,
          previous: list[dict] | None = None) -> tuple[list[Case], str]:
    """Cases of one hook and how they were obtained: gherkin, model, mixed or none.
    feedback (G2 findings by criterion) sends those criteria to the model with the rejected cases."""
    feedback = feedback or {}
    criteria = related(hook, analysis)
    rows = {ac["id"]: examples(ac.get("gherkin", "")) for ac in criteria}
    cases: list[Case] = []
    pending = {}
    for ac in criteria:
        found = direct(hook, ac["id"], rows[ac["id"]])
        if found and len(found) >= MIN_CASES and ac["id"] not in feedback:
            cases += found
        else:
            pending[ac["id"]] = rows[ac["id"]]
    if not pending:
        return cases, "gherkin" if cases else "none"
    wanted = {f"{ac}-{index}" for ac, table in pending.items() for index in range(1, len(table) + 1)}
    try:
        rejected = {"why": [message for ac in pending for message in feedback.get(ac, [])],
                    "cases": [case for case in previous or [] if case.get("ac") in pending]}
        answer = ask(llm, hook, app, analysis, [ac for ac in criteria if ac["id"] in pending], pending,
                     rejected if rejected["why"] else None)
        cases += check(hook, answer, wanted, set(pending))
    except BudgetExceeded:
        return cases, "budget"
    return cases, "mixed" if len(pending) < len(criteria) else "model"


def write(workspace_path, root, hook: dict, cases: list[Case]) -> str:
    relative = f"{CASES}/{hook['id']}.json"
    target = workspace_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "hook": hook["id"], "method": hook["method"],
               "cases": [case.model_dump(mode="json") for case in sorted(cases, key=lambda c: c.id)]}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return relative


def test_class(ac: str) -> str:
    """xunit class for one criterion; the JUnit class name carries the AC id."""
    ident = ac.replace("-", "_")
    return (
        "using Xunit;\n\n"
        "namespace App.Acceptance.Tests.Generated;\n\n"
        f"public sealed class {ident}_Tests\n"
        "{\n"
        f"    public static TheoryData<string> Cases => HookCases.For(\"{ac}\");\n\n"
        f"    [Theory, Trait(\"AC\", \"{ac}\"), MemberData(nameof(Cases))]\n"
        f"    public void {ident}(string key) => HookCases.Run(key);\n"
        "}\n"
    )

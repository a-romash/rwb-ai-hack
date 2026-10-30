"""Общие чистые операции анализа ссылок, Gherkin и временных границ."""
from __future__ import annotations

import re
from decimal import Decimal

from gherkin.parser import Parser
from gherkin.errors import CompositeParserException

from contracts.app import App


def parse_gherkin(text: str) -> dict | None:
    try:
        return Parser().parse(text)
    except (CompositeParserException, ValueError, TypeError):
        return None


def normalize_gherkin(text: str) -> str:
    """Исправляет только распространённое оформление ключевых слов шагов."""
    return re.sub(r"^(\s*)(Дано|Допустим|Когда|Тогда|И|Но):[ \t]*", r"\1\2 ", text, flags=re.MULTILINE)


def scenarios(document: dict) -> list[dict]:
    feature = document.get("feature", {})
    result: list[dict] = []

    def visit(children: list[dict]) -> None:
        for child in children:
            if "scenario" in child:
                result.append(child["scenario"])
            elif "rule" in child:
                visit(child["rule"].get("children", []))
    visit(feature.get("children", []))
    return result


def number(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if not isinstance(value, str):
        return None
    duration = re.fullmatch(r"P(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?", value)
    if duration and any(duration.groups()):
        return sum((Decimal(part or 0) * factor for part, factor in zip(duration.groups(), (86400, 3600, 60, 1))), Decimal(0))
    clock = re.fullmatch(r"(\d{2}):(\d{2})(?::(\d{2}))?", value)
    if clock:
        h, m, s = (int(v or 0) for v in clock.groups())
        return Decimal(h * 3600 + m * 60 + s)
    try:
        return Decimal(value.replace(",", "."))
    except Exception:
        return None


def implicit_events(app: App) -> set[str]:
    """Совместимость примеров §3.6; соглашение генератора отмечено в отчёте."""
    irregular = {"take": "taken", "give": "given", "send": "sent", "do": "done", "make": "made", "begin": "begun", "run": "run"}
    names: set[str] = set()
    for machine in app.state_machines.root.values():
        for transition in machine.transitions:
            words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", transition.name.replace("_", " ")) or [transition.name]
            verb = words[0].lower()
            past = irregular.get(verb, verb + ("d" if verb.endswith("e") else "ed"))
            names.add(machine.entity + past[:1].upper() + past[1:] + "".join(w.title() for w in words[1:]))
            names.add(machine.entity + "".join(word.title() for word in words))
    return names


def operation_exists(app: App, op: str) -> bool:
    if "." not in op:
        return op in app.commands.root
    entity, verb = op.rsplit(".", 1)
    return entity in app.entities.root and verb in ("create", "read", "update", "delete")

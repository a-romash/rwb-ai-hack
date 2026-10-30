"""Read-only view of app.json for the ui stage and gate G1.5.

Works on the raw dict until contracts/app.py lands; only the keys of §3.6 are used.
"""
from dataclasses import dataclass
from typing import Any

CRUD = ("create", "read", "update", "delete")


@dataclass(frozen=True)
class AppView:
    raw: dict[str, Any]

    def _section(self, key: str) -> dict[str, Any]:
        return self.raw.get(key) or {}

    @property
    def lang(self) -> str:
        return (self.raw.get("meta") or {}).get("lang", "ru-RU")

    @property
    def entities(self) -> dict[str, Any]:
        return self._section("entities")

    @property
    def roles(self) -> dict[str, Any]:
        return self._section("roles")

    @property
    def commands(self) -> dict[str, Any]:
        return self._section("commands")

    @property
    def queries(self) -> dict[str, Any]:
        return self._section("queries")

    @property
    def hooks(self) -> dict[str, Any]:
        return self._section("hooks")

    @property
    def params(self) -> dict[str, Any]:
        return self._section("params")

    @property
    def machines(self) -> dict[str, Any]:
        return self._section("state_machines")

    @property
    def seed(self) -> dict[str, list[dict[str, Any]]]:
        return self._section("seed")

    def fields(self, entity: str) -> dict[str, Any]:
        return (self.entities.get(entity) or {}).get("fields") or {}

    def field(self, path: str) -> dict[str, Any] | None:
        """Entity.field or Command.input -> field definition."""
        owner, _, name = path.partition(".")
        if owner in self.entities:
            return self.fields(owner).get(name)
        if owner in self.commands:
            return (self.commands[owner].get("input") or {}).get(name)
        return None

    def operation_exists(self, op: str) -> bool:
        entity, _, verb = op.partition(".")
        return op in self.commands if not verb else entity in self.entities and verb in CRUD

    def roles_for(self, op: str) -> set[str]:
        """Roles allowed to perform an operation; permissions win, command.roles is the fallback."""
        granted = {p["role"] for p in self.raw.get("permissions") or [] if p.get("op") == op}
        if not granted and op in self.commands:
            granted = set(self.commands[op].get("roles") or [])
        return granted

    def entity_of(self, op: str) -> str | None:
        if op in self.commands:
            return self.commands[op].get("entity")
        entity = op.partition(".")[0]
        return entity if entity in self.entities else None

    def machine_of(self, entity: str) -> dict[str, Any] | None:
        return next((m for m in self.machines.values() if m.get("entity") == entity), None)

    def states(self) -> set[str]:
        return {s for m in self.machines.values() for s in m.get("states") or []}

    def timer_fields(self, entity: str) -> set[str]:
        machine = self.machine_of(entity) or {}
        return {t["trigger"]["timer"] for t in machine.get("transitions") or []
                if "timer" in (t.get("trigger") or {})}

    def events(self, entity: str | None = None) -> set[str]:
        """Explicit events plus the ones the generator derives from transitions (OrderShipped, …)."""
        names = set() if entity else set(self._section("events"))
        for machine in self.machines.values():
            if entity and machine.get("entity") != entity:
                continue
            for transition in machine.get("transitions") or []:
                names.add(derived_event(machine["entity"], transition["name"]))
        return names

    def event_exists(self, name: str) -> bool:
        if name in self._section("events"):
            return True
        # The past-tense spelling is the generator's; accept any short suffix after Entity+Transition.
        for machine in self.machines.values():
            for transition in machine.get("transitions") or []:
                if name == derived_event(machine["entity"], transition["name"]):
                    return True  # take_overdue -> TicketTakenOverdue: the verb is inflected mid-name
                stem = machine["entity"] + _pascal(transition["name"])
                if name.startswith(stem) and len(name) - len(stem) <= 3:
                    return True
        return False


def _pascal(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("_"))


def derived_event(entity: str, transition: str) -> str:
    """take -> OrderTaken, expire -> OrderExpired, close -> OrderClosed, stop -> OrderStopped."""
    irregular = {"take": "taken", "give": "given", "write": "written", "send": "sent", "begin": "begun",
                 "set": "set", "put": "put", "get": "got", "make": "made", "hold": "held", "leave": "left"}
    verb, sep, rest = transition.partition("_")
    if verb in irregular:
        past = irregular[verb]
    elif verb.endswith("e"):
        past = verb + "d"
    elif verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        past = verb[:-1] + "ied"
    elif (sum(c in "aeiou" for c in verb) == 1 and len(verb) >= 3 and verb[-1] not in "aeiouwxy"
          and verb[-2] in "aeiou" and verb[-3] not in "aeiou"):   # one-syllable CVC: stop -> stopped
        past = verb + verb[-1] + "ed"
    else:
        past = verb + "ed"
    return entity + _pascal(past + sep + rest)

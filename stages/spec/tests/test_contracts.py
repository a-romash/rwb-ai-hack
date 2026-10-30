"""Независимые проверки S0: python -m unittest discover -s stages/spec/tests -v."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from contracts.analysis import Analysis, DataCard, Question
from contracts.app import (
    App, CommandsSection, CustomSection, EntitiesSection, EventsSection,
    HooksSection, IntegrationsSection, MetaSection, NotificationsSection,
    ParamsSection, PermissionsSection, QueriesSection, RolesSection,
    ScenariosSection, SchedulesSection, SeedSection, StateMachinesSection,
    TypesSection, dependents,
)
from contracts.export import export_schemas

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "contracts" / "fixtures" / "tickets"


def read_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = read_fixture("analysis")

    def test_fixture_and_serialization(self) -> None:
        model = Analysis.model_validate(self.data)
        self.assertEqual(Analysis.model_validate_json(model.model_dump_json()), model)
        self.assertEqual(len(model.requirements), 9)

    def test_source_fragments_and_quotes_match_original(self) -> None:
        text = (FIXTURES / "requirements.md").read_text(encoding="utf-8")
        model = Analysis.model_validate(self.data)
        sources = {source.id: source.text for source in model.sources}
        covered: set[str] = set()
        for source in model.sources:
            self.assertIn(source.text, text)
        for req in model.requirements:
            self.assertTrue(req.quote)
            self.assertTrue(req.source)
            self.assertTrue(any(req.quote in sources[source] for source in req.source))
            covered.update(req.source)
        self.assertEqual(covered, set(sources))

    def test_all_identified_lists_reject_duplicates(self) -> None:
        # NFR нет в исходном задании домена; добавляем только для проверки модели.
        self.data["nfr"] = [{"id": "NFR-01", "text": "Время ответа", "metric": "p95 ≤ 2 с", "verify": "Нагрузочный тест"}]
        names = ("sources", "requirements", "roles", "issues", "questions", "assumptions", "user_stories", "rules", "acceptance", "nfr")
        for name in names:
            with self.subTest(section=name):
                broken = copy.deepcopy(self.data)
                broken[name].append(copy.deepcopy(broken[name][0]))
                with self.assertRaisesRegex(ValidationError, "Повторяющиеся id"):
                    Analysis.model_validate(broken)

    def test_lists_without_id_do_not_require_invented_ids(self) -> None:
        Analysis.model_validate(self.data)
        self.assertNotIn("id", self.data["glossary"][0])

    def test_unknown_requirement_type_characteristic_module_platform(self) -> None:
        changes = [
            ("requirements", 0, "type", "magic"),
            ("issues", 0, "characteristic", "неизвестно"),
        ]
        for section, index, key, value in changes:
            with self.subTest(section=section):
                broken = copy.deepcopy(self.data)
                broken[section][index][key] = value
                with self.assertRaises(ValidationError):
                    Analysis.model_validate(broken)
        for key in ("modules", "platforms"):
            with self.subTest(profile=key):
                broken = copy.deepcopy(self.data)
                broken["profile"][key] = ["unknown"]
                with self.assertRaises(ValidationError):
                    Analysis.model_validate(broken)

    def test_extra_field_rejected_at_root_and_nested_model(self) -> None:
        for section in (None, "requirements", "sources", "rules", "questions"):
            with self.subTest(section=section):
                broken = copy.deepcopy(self.data)
                target = broken if section is None else broken[section][0]
                target["unexpected"] = True
                with self.assertRaises(ValidationError):
                    Analysis.model_validate(broken)

    def test_question_default_and_answer_author(self) -> None:
        question = self.data["questions"][0]
        for patch in ({"default": "Нет такого варианта"}, {"answer": None}, {"answered_by": None}, {"options": ["Да", "Да"]}):
            with self.subTest(patch=patch):
                with self.assertRaises(ValidationError):
                    Question.model_validate(question | patch)
        pending = question | {"answer": None, "answered_by": None}
        self.assertIsNone(Question.model_validate(pending).answer)
        # Ответ человека может отличаться от предложенных вариантов.
        Question.model_validate(question | {"answer": "Уточнённый календарь", "answered_by": "human"})

    def test_schema_version_required_and_closed(self) -> None:
        for value in (0, 2):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Analysis.model_validate(self.data | {"schema_version": value})
        del self.data["schema_version"]
        with self.assertRaises(ValidationError):
            Analysis.model_validate(self.data)

    def test_data_card_schema_alias_round_trip(self) -> None:
        payload = {"file": "sample.json", "records": 1, "schema": {"value": "int"}, "anomalies": [], "samples": [{"value": 1}]}
        card = DataCard.model_validate(payload)
        self.assertEqual(card.model_dump(), payload)
        self.assertEqual(DataCard.model_validate_json(card.model_dump_json()), card)
        with self.assertRaises(ValidationError):
            DataCard.model_validate(payload | {"records": -1})


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = read_fixture("app")

    def test_fixture_and_alias_round_trip(self) -> None:
        model = App.model_validate(self.data)
        self.assertEqual(App.model_validate_json(model.model_dump_json()), model)
        dumped = model.model_dump(mode="json", exclude_none=True)
        self.assertIn("from", dumped["state_machines"]["TicketFlow"]["transitions"][0])
        self.assertIn("in", dumped["hooks"]["SlaDeadline"])
        self.assertNotIn("from_", model.model_dump_json())

    def test_every_section_has_an_independent_model(self) -> None:
        sections = {
            "meta": MetaSection, "params": ParamsSection, "types": TypesSection,
            "entities": EntitiesSection, "roles": RolesSection, "permissions": PermissionsSection,
            "state_machines": StateMachinesSection, "hooks": HooksSection,
            "commands": CommandsSection, "queries": QueriesSection,
            "events": EventsSection, "integrations": IntegrationsSection,
            "schedules": SchedulesSection, "notifications": NotificationsSection,
            "seed": SeedSection, "scenarios": ScenariosSection, "custom": CustomSection,
        }
        for key, model in sections.items():
            with self.subTest(section=key):
                model.model_validate(self.data[key])
                model.model_json_schema()

    def test_closed_vocabularies(self) -> None:
        modifications = [
            (self.data["entities"]["Ticket"]["fields"]["title"], "type", "varchar"),
            (self.data["types"]["Priority"], "kind", "class"),
            (self.data["hooks"]["SlaDeadline"], "kind", "database"),
            (self.data["permissions"][0], "scope", "global"),
            (self.data["permissions"][0], "op", "Ticket.execute"),
            (self.data["notifications"]["TicketOverdue"], "channels", ["telegram"]),
            (self.data["meta"], "modules", ["unknown"]),
        ]
        for target, key, invalid in modifications:
            old = target[key]
            with self.subTest(key=key, value=invalid):
                target[key] = invalid
                with self.assertRaises(ValidationError):
                    App.model_validate(self.data)
                target[key] = old

    def test_nested_extra_fields_rejected(self) -> None:
        targets = [self.data, self.data["meta"], self.data["entities"]["Ticket"],
                   self.data["entities"]["Ticket"]["fields"]["title"], self.data["hooks"]["SlaDeadline"],
                   self.data["commands"]["TakeTicket"], self.data["queries"]["OpenTickets"],
                   self.data["state_machines"]["TicketFlow"]["transitions"][0]["trigger"]]
        for index, target in enumerate(targets):
            with self.subTest(index=index):
                target["unexpected"] = True
                with self.assertRaises(ValidationError):
                    App.model_validate(self.data)
                del target["unexpected"]

    def test_trigger_closed_and_single_kind(self) -> None:
        transition = self.data["state_machines"]["TicketFlow"]["transitions"][0]
        for trigger in ({"unknown": "something"}, {"command": "TakeTicket", "timer": "due_at"}):
            with self.subTest(trigger=trigger):
                transition["trigger"] = trigger
                with self.assertRaises(ValidationError):
                    App.model_validate(self.data)

    def test_semantic_violations_remain_available_to_g1(self) -> None:
        # Иначе G1 не сможет выдать SM_NO_TRIGGER и REF_UNRESOLVED по своим кодам.
        self.data["state_machines"]["TicketFlow"]["transitions"][0].pop("trigger")
        self.data["entities"]["Ticket"]["fields"]["priority"]["ref"] = "MissingType"
        App.model_validate(self.data)

    def test_fixture_references_resolve(self) -> None:
        analysis = Analysis.model_validate(read_fixture("analysis"))
        rules = {item.id for item in analysis.rules}
        acceptance = {item.id for item in analysis.acceptance}
        app = App.model_validate(self.data)
        for entity in app.entities.root.values():
            if entity.owner:
                self.assertIn(entity.owner, entity.fields)
            for field in entity.fields.values():
                if field.type == "ref":
                    self.assertIn(field.ref, app.entities.root)
                elif field.type == "enum":
                    self.assertIn(field.ref, app.types.root)
                if field.computed_by:
                    self.assertIn(field.computed_by, app.hooks.root)
                if field.machine:
                    self.assertIn(field.machine, app.state_machines.root)
        for hook in app.hooks.root.values():
            self.assertIn(hook.rule, rules)
            self.assertTrue(set(hook.traces) <= acceptance)
            self.assertTrue(set(hook.params) <= app.params.root.keys())
        self.assertEqual({hook.rule for hook in app.hooks.root.values()}, rules)
        for machine in app.state_machines.root.values():
            self.assertIn(machine.entity, app.entities.root)
            self.assertIn(machine.initial, machine.states)
            self.assertTrue(set(machine.final) <= set(machine.states))
            for transition in machine.transitions:
                self.assertTrue(set(transition.from_) <= set(machine.states))
                self.assertIn(transition.to, machine.states)
                self.assertTrue(set(transition.roles) <= app.roles.root.keys())
                if transition.guard:
                    self.assertIn(transition.guard, app.hooks.root)
                if transition.trigger and transition.trigger.command:
                    self.assertIn(transition.trigger.command, app.commands.root)

    def test_no_crud_or_generated_events_written(self) -> None:
        self.assertEqual(self.data["events"], {})
        self.assertTrue(all("." not in name for name in self.data["commands"]))


class DependentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = read_fixture("app")

    def paths(self, path: str) -> list[str]:
        return dependents(App.model_validate(self.data), path)

    def test_parameter_to_hook_to_field_to_timer_to_notification(self) -> None:
        paths = self.paths("params.SLA_HIGH")
        expected = {"hooks.SlaDeadline", "entities.Ticket.fields.due_at",
                    "state_machines.TicketFlow.transitions[2]", "notifications.TicketOverdue"}
        self.assertTrue(expected <= set(paths), paths)
        self.assertEqual(paths, sorted(set(paths)))
        self.assertNotIn("params.SLA_HIGH", paths)

    def test_field_to_query_hook_and_seed(self) -> None:
        for path, expected in [
            ("entities.Ticket.fields.created_at", "hooks.WorkCalendar"),
            ("entities.Ticket.fields.status", "queries.OpenTickets"),
            ("entities.Ticket.fields.title", "seed.Ticket[0].title"),
            ("entities.Ticket.fields.due_at", "queries.MyTickets"),
        ]:
            with self.subTest(path=path):
                self.assertIn(expected, self.paths(path))

    def test_enum_reference(self) -> None:
        self.assertIn("entities.Ticket.fields.priority", self.paths("types.Priority"))

    def test_role_command_permissions_and_transition(self) -> None:
        paths = self.paths("roles.engineer")
        for expected in ("commands.TakeTicket", "permissions[3]", "queries.OpenTickets", "state_machines.TicketFlow.transitions[0]"):
            self.assertIn(expected, paths)

    def test_query_select_and_input_reference(self) -> None:
        self.data["hooks"]["SlaDeadline"]["select"] = "OpenTickets"
        self.data["commands"]["TakeTicket"]["input"] = {"priority": {"type": "enum", "ref": "Priority"}}
        self.assertIn("hooks.SlaDeadline", self.paths("queries.OpenTickets"))
        self.assertIn("commands.TakeTicket.input.priority", self.paths("types.Priority"))

    def test_event_and_schedule_triggers(self) -> None:
        transition = self.data["state_machines"]["TicketFlow"]["transitions"][0]
        for kind, section in (("event", "events"), ("schedule", "schedules")):
            with self.subTest(kind=kind):
                transition["trigger"] = {kind: "ExternalSignal"}
                self.data[section]["ExternalSignal"] = {}
                self.assertIn("state_machines.TicketFlow.transitions[0]", self.paths(f"{section}.ExternalSignal"))

    def test_declared_event_to_notification(self) -> None:
        self.data["events"]["TicketExpired"] = {}
        self.assertIn("notifications.TicketOverdue", self.paths("events.TicketExpired"))

    def test_transition_effect_and_state_index(self) -> None:
        self.assertIn("commands.TakeTicket", self.paths("state_machines.TicketFlow.transitions[0]"))
        self.assertIn("state_machines.TicketFlow.transitions[0]", self.paths("state_machines.TicketFlow.states[0]"))

    def test_alias_paths_are_equivalent(self) -> None:
        self.assertEqual(self.paths("app.params.SLA_HIGH"), self.paths("/params/SLA_HIGH"))
        self.assertEqual(self.paths("params[SLA_HIGH]"), self.paths("params.SLA_HIGH"))

    def test_analysis_trace_paths(self) -> None:
        self.assertIn("hooks.SlaDeadline", self.paths("analysis.rules[BR-02]"))
        self.assertIn("hooks.ResolutionRequired", self.paths("analysis.acceptance[AC-03]"))

    def test_cycles_terminate_and_do_not_mutate_app(self) -> None:
        app = App.model_validate(self.data)
        before = app.model_dump_json()
        paths = dependents(app, "state_machines.TicketFlow")
        self.assertTrue(paths)
        self.assertEqual(before, app.model_dump_json())
        self.assertFalse(any(path.startswith("state_machines.TicketFlow") for path in paths))

    def test_similar_identifiers_do_not_match(self) -> None:
        self.data["params"]["SLA_HIGHER"] = copy.deepcopy(self.data["params"]["SLA_HIGH"])
        self.assertEqual(self.paths("params.SLA_HIGHER"), [])

    def test_transitive_field_does_not_mark_whole_entity(self) -> None:
        paths = self.paths("hooks.SlaDeadline")
        self.assertIn("entities.Ticket.fields.status", paths)
        self.assertFalse([p for p in paths if p.startswith("permissions") or p == "seed.Ticket"], paths)
        self.assertIn("seed.Ticket", self.paths("entities.Ticket.fields.title"))

    def test_unrelated_entity_is_not_affected(self) -> None:
        self.data["entities"]["Unrelated"] = {"label": "Независимая", "fields": {"title": {"type": "string"}}, "traces": []}
        self.assertEqual(self.paths("entities.Unrelated.fields.title"), [])

    def test_opaque_sections_retain_explicit_links(self) -> None:
        self.data["custom"] = [{"description": "Расширение", "reference": "Ticket.created_at"}]
        self.assertIn("custom[0].reference", self.paths("entities.Ticket.fields.created_at"))


class ExportTests(unittest.TestCase):
    def test_schema_export_is_deterministic_and_uses_wire_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)
            paths = export_schemas(destination)
            original = {path.name: path.read_bytes() for path in paths}
            export_schemas(destination)
            self.assertEqual(original, {path.name: path.read_bytes() for path in paths})
            self.assertEqual(set(original), {"analysis.schema.json", "app.schema.json"})
            analysis = json.loads(original["analysis.schema.json"])
            app = json.loads(original["app.schema.json"])
            self.assertEqual(analysis["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIn("schema", analysis["$defs"]["DataCard"]["properties"])
            self.assertIn("from", app["$defs"]["Transition"]["properties"])
            self.assertIn("in", app["$defs"]["Hook"]["properties"])
            for schema in (analysis, app):
                self.assertIs(schema["additionalProperties"], False)
                for definition in schema["$defs"].values():
                    if definition.get("type") == "object" and "properties" in definition:
                        self.assertIs(definition["additionalProperties"], False)

    def test_checked_in_schemas_are_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for path in export_schemas(Path(tmp)):
                saved = ROOT / "contracts" / "schemas" / path.name
                self.assertEqual(json.loads(saved.read_text(encoding="utf-8")), json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()

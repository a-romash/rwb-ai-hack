import unittest
from pydantic import BaseModel, ConfigDict, Field
from harness.normalization import (
    normalize_response,
    normalize_app,
    normalize_ui,
    identifier,
)


class Packet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_count: int
    enabled: bool = False
    tags: list[str] = Field(default_factory=list)


class NormalizationTests(unittest.TestCase):
    def test_wrapped_json_alias_scalar_and_unknown_are_audited(self):
        value, changes = normalize_response(
            '```json\n{"result":{"itemCount":"3","extra":"keep in audit"}}\n```', Packet
        )
        self.assertEqual(Packet.model_validate(value).item_count, 3)
        self.assertTrue(any(c.get("before") == "keep in audit" for c in changes))
        self.assertEqual(normalize_response(value, Packet)[0], value)

    def test_hook_rename_updates_typed_refs_without_touching_copy(self):
        old = "Enforce Server Side Business Validation"
        data = {
            "hooks": {old: {"kind": "policy", "rule": "BR-12"}},
            "entities": {
                "Room": {"fields": {"can Book": {"type": "bool", "computed_by": old}}}
            },
            "state_machines": {
                "Flow": {"entity": "Room", "transitions": [{"guard": old}]}
            },
            "commands": {
                "Book Room": {"entity": "Room", "effects": [old + "()"], "roles": []}
            },
            "permissions": [{"role": "ROLE-01", "op": "Book Room", "scope": "all"}],
            "custom": [{"description": old}],
            "roles": {"ROLE-01": {"name": "Админ"}},
        }
        app, changes = normalize_app(data)
        self.assertIn("EnforceServerSideBusinessValidation", app["hooks"])
        self.assertEqual(
            app["entities"]["Room"]["fields"]["can_book"]["computed_by"],
            "EnforceServerSideBusinessValidation",
        )
        self.assertEqual(
            app["state_machines"]["Flow"]["transitions"][0]["guard"],
            "EnforceServerSideBusinessValidation",
        )
        self.assertEqual(app["permissions"][0]["op"], "BookRoom")
        self.assertEqual(app["custom"], data["custom"])
        self.assertEqual(normalize_app(app)[0], app)
        self.assertEqual(data["commands"]["Book Room"]["effects"], [old + "()"])
        self.assertTrue(changes)

    def test_collisions_preserve_conflicting_definitions_and_valid_names(self):
        app, changes = normalize_app(
            {"hooks": {"Bad Name": {"rule": "BR-01"}, "BadName": {"rule": "BR-02"}}}
        )
        self.assertEqual(len(app["hooks"]), 2)
        self.assertEqual(app["hooks"]["BadName"], {"rule": "BR-02"})
        self.assertTrue(any(c["reason"] == "name_collision" for c in changes))
        self.assertEqual(normalize_app(app)[0], app)

    def test_cyrillic_and_fuzzy_references(self):
        app, _ = normalize_app(
            {
                "entities": {"Комната": {"fields": {}}},
                "queries": {"Rooms": {"entity": "комната"}},
            }
        )
        self.assertIn("Komnata", app["entities"])
        self.assertEqual(app["queries"]["Rooms"]["entity"], "Komnata")
        self.assertEqual(identifier("123 room"), "N123Room")

    def test_ui_links_follow_screen_renames(self):
        doc = {
            "screens": {
                "Room List": {
                    "nav": ["Room List"],
                    "title": "Room List",
                    "roles": ["ROLE-01"],
                }
            },
            "home": {"ROLE-01": {"web": "Room List"}},
            "menus": {"ROLE-01": {"web": ["Room List"]}},
        }
        ui, _ = normalize_ui(doc, {})
        self.assertIn("RoomList", ui["screens"])
        self.assertEqual(ui["home"]["ROLE-01"]["web"], "RoomList")
        self.assertEqual(ui["screens"]["RoomList"]["title"], "Room List")
        self.assertEqual(normalize_ui(ui, {})[0], ui)

    def test_patch_paths_are_not_guessed_in_gateway(self):
        from stages.analysis.patching import PatchResponse

        raw = {
            "operations": [
                {"op": "replace", "path": "/hooks/Bad Name/rule", "value": "BR-02"}
            ]
        }
        value, _ = normalize_response(raw, PatchResponse)
        self.assertEqual(value["operations"][0]["path"], raw["operations"][0]["path"])

    def test_union_keeps_each_walk_step_and_stable_ids(self):
        from contracts.ui import Walk

        raw = {
            "role": "ROLE-01",
            "platform": "web",
            "steps": [
                {"open": "Room List"},
                {"tap": "BookRoom"},
                {"expect": {"screen": "Room List"}},
            ],
            "covers": ["AC-01"],
        }
        value, _ = normalize_response(raw, Walk)
        model = Walk.model_validate(value)
        self.assertEqual(model.steps[0].open, "RoomList")
        self.assertEqual(model.steps[1].tap, "BookRoom")
        self.assertEqual(model.covers, ["AC-01"])

    def test_opaque_json_data_is_not_unwrapped(self):
        from pydantic import JsonValue

        class Data(BaseModel):
            payload: JsonValue

        raw = {"payload": {"data": {"room": {"name": "result"}}}}
        self.assertEqual(normalize_response(raw, Data)[0], raw)

    def test_patch_normalization_does_not_bypass_authorization(self):
        from harness.normalization import normalize_patch
        from stages.analysis.patching import apply_patch, PatchResponse, PatchRejected
        from contracts.gates import Finding

        doc = {
            "hooks": {"BadName": {"rule": "BR-01"}},
            "roles": {"Admin": {"name": "Админ"}},
        }
        raw = {
            "operations": [{"op": "replace", "path": "/roles/admin/name", "value": "X"}]
        }
        mapped, _ = normalize_patch(raw, doc)
        self.assertEqual(mapped["operations"][0]["path"], "/roles/Admin/name")
        with self.assertRaises(PatchRejected):
            apply_patch(
                doc,
                PatchResponse.model_validate(mapped),
                [
                    Finding(
                        path="hooks.BadName", code="ERR", message="x", severity="error"
                    )
                ],
            )

    def test_compatible_aliases_merge_without_losing_values(self):
        app, _ = normalize_app(
            {"hooks": {"Bad Name": {"rule": "BR-01"}, "BadName": {"kind": "policy"}}}
        )
        self.assertEqual(app["hooks"], {"BadName": {"rule": "BR-01", "kind": "policy"}})

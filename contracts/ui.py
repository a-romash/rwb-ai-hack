"""ui.json: screens by role and platform, widgets, actions, states and user-story walks.

Owner: Artem. Consumers: scaffold (screens, page objects), tests (E2E from walks), report.
The schema checks only the file itself; references to app.json are checked by gate G1.5.
Human-readable catalog: contracts/ui_catalog.md.
"""
import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, model_validator

Platform = Literal["web", "mobile"]
Pattern = Literal["list", "detail", "form", "wizard", "dashboard", "map", "feed",
                  "action", "settings", "calendar", "kanban"]
WidgetKind = Literal["field", "status", "countdown", "kpi", "timeline", "map_layer",
                     "action_button", "scan", "file"]
StepKind = Literal["open", "fill", "tap", "scan", "expect"]
DeviceFeature = Literal["location", "local_notification", "external_link", "scan_code", "file_pick"]
ScreenState = Literal["loading", "empty", "error", "forbidden", "offline"]
SourceKind = Literal["query", "entity", "command", "params"]
Aggregate = Literal["count", "sum", "avg", "min", "max"]

SCREEN_NAME = r"^[A-Z][A-Za-z0-9]*$"
# Names follow app.json, which allows any identifier (a spec may name a command startSession); G1.5 checks they exist.
FIELD_PATH = r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$"   # Entity.field or Command.input
OPERATION = r"^[A-Za-z_][A-Za-z0-9_]*(\.(create|read|update|delete))?$"  # command name or Entity.op
TESTID = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*\.[a-z][a-z0-9]*([.-][a-z0-9]+)*$"
COPY_KEY = r"^[a-z][A-Za-z0-9_-]*(\.[A-Za-z0-9_-]+)*$"
SEED_ROW = r"^[A-Z][A-Za-z0-9]*\[\d+\]$"
SEED_VALUE = r"^[A-Z][A-Za-z0-9]*\[\d+\](\.[a-z][a-z0-9_]*)?$"

# Mandatory screen states for screens with a data source; the model writes only the texts.
REQUIRED_STATES: dict[str, tuple[str, ...]] = {
    "web": ("loading", "empty", "error", "forbidden"),
    "mobile": ("loading", "empty", "error", "forbidden", "offline"),
}

# Which source kinds a pattern accepts; an empty tuple means the screen has no source.
PATTERN_SOURCES: dict[str, tuple[str, ...]] = {
    "list": ("query", "entity"),
    "detail": ("entity",),
    "form": ("entity", "command"),
    "wizard": ("command",),
    "dashboard": (),
    "map": ("query", "entity"),
    "feed": ("query", "entity"),
    "action": ("command", "entity"),
    "settings": ("params",),
    "calendar": ("query", "entity"),
    "kanban": ("query", "entity"),
}

PATTERN_WIDGETS: dict[str, frozenset[str]] = {
    "list": frozenset({"field", "status", "countdown", "file"}),
    "detail": frozenset({"field", "status", "countdown", "timeline", "map_layer", "action_button", "file"}),
    "form": frozenset({"field", "file", "scan"}),
    "wizard": frozenset({"field", "file", "scan"}),
    "dashboard": frozenset({"kpi", "map_layer", "timeline"}),
    "map": frozenset({"map_layer", "field", "status", "action_button"}),
    "feed": frozenset({"field", "status", "countdown", "timeline"}),
    "action": frozenset({"field", "status", "countdown", "action_button", "scan", "map_layer", "file"}),
    "settings": frozenset({"field"}),
    "calendar": frozenset({"field", "status", "countdown"}),
    "kanban": frozenset({"field", "status", "countdown"}),
}

# Reference a widget must carry, by kind.
WIDGET_REFS: dict[str, tuple[str, ...]] = {
    "field": ("field",),
    "status": ("field",),
    "countdown": ("field",),
    "kpi": ("query",),
    "timeline": ("field",),
    "map_layer": ("query",),
    "action_button": ("command",),
    "scan": ("field",),
    "file": ("field",),
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def screen_kebab(name: str) -> str:
    """TicketList -> ticket-list; testids of a screen start with this prefix."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "-", name).lower()


class Source(_Strict):
    """Exactly one of the fields: where the screen data comes from in app.json."""
    query: str | None = None
    entity: str | None = None
    command: str | None = None
    params: list[str] | None = None

    @property
    def kind(self) -> SourceKind:
        return next(k for k in ("query", "entity", "command", "params") if getattr(self, k) is not None)

    @model_validator(mode="after")
    def _one(self) -> "Source":
        if sum(getattr(self, k) is not None for k in ("query", "entity", "command", "params")) != 1:
            raise ValueError("source: укажите ровно одно из query, entity, command, params")
        return self


class Widget(_Strict):
    kind: WidgetKind
    testid: str = Field(pattern=TESTID)
    field: str | None = Field(default=None, pattern=FIELD_PATH)
    query: str | None = None
    command: str | None = Field(default=None, pattern=OPERATION)
    agg: Aggregate | None = None        # kpi only; default count
    label: str | None = None            # copy key; default is the field label from app.json
    group: str | None = None            # copy key of a field group (card section, form fieldset)

    @model_validator(mode="after")
    def _refs(self) -> "Widget":
        for ref in WIDGET_REFS[self.kind]:
            if getattr(self, ref) is None:
                raise ValueError(f"виджет {self.kind}: нужно поле {ref}")
        if self.agg is not None and self.kind != "kpi":
            raise ValueError("agg допустим только у kpi")
        if self.kind == "kpi" and self.agg not in (None, "count") and self.field is None:
            raise ValueError(f"kpi с agg {self.agg}: нужно поле field")
        return self


class Filter(_Strict):
    field: str = Field(pattern=FIELD_PATH)
    testid: str = Field(pattern=TESTID)


class Action(_Strict):
    command: str = Field(pattern=OPERATION)   # command name or Entity.create|update|delete
    testid: str = Field(pattern=TESTID)
    confirm: bool = False
    copy_key: str | None = Field(default=None, alias="copy", pattern=COPY_KEY)  # confirmation text
    then: str | None = Field(default=None, pattern=SCREEN_NAME)  # screen opened after success

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)


class Screen(_Strict):
    platform: Platform
    roles: list[str] = Field(min_length=1)
    pattern: Pattern
    title: str
    source: Source | None = None
    widgets: list[Widget] = Field(default_factory=list)
    filters: list[Filter] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    live: list[str] = Field(default_factory=list)       # app events that refresh the screen (SSE)
    states: dict[ScreenState, str] = Field(default_factory=dict)
    nav: list[str] = Field(default_factory=list)        # screens reachable from this one

    @property
    def has_data(self) -> bool:
        """Screens that load data must define all REQUIRED_STATES (checked by G1.5)."""
        return self.source is not None or any(w.kind in ("kpi", "map_layer", "timeline") for w in self.widgets)

    def testids(self) -> list[str]:
        return [w.testid for w in self.widgets] + [f.testid for f in self.filters] + [a.testid for a in self.actions]

    @model_validator(mode="after")
    def _pattern(self) -> "Screen":
        allowed = PATTERN_SOURCES[self.pattern]
        if self.source is None and allowed and self.pattern not in ("feed",):
            raise ValueError(f"паттерн {self.pattern}: нужен source ({', '.join(allowed)})")
        if self.source is not None and self.source.kind not in allowed:
            raise ValueError(f"паттерн {self.pattern}: source {self.source.kind} недопустим")
        for widget in self.widgets:
            if widget.kind not in PATTERN_WIDGETS[self.pattern]:
                raise ValueError(f"паттерн {self.pattern}: виджет {widget.kind} недопустим")
        if "offline" in self.states and self.platform != "mobile":
            raise ValueError("состояние offline есть только у mobile")
        return self


class SeedRef(_Strict):
    seed: str = Field(pattern=SEED_VALUE)    # "Ticket[0]" or "Ticket[0].title"


class ParamRef(_Strict):
    param: str                               # key of app.json params


class GenRef(_Strict):
    gen: Literal["valid"]                    # any valid value of the target type, made by the test kit


Value = SeedRef | ParamRef | GenRef | str | int | float | bool   # bare scalar = literal, G1.5 warns


class RowRef(_Strict):
    seed: str = Field(pattern=SEED_ROW)


class OpenStep(_Strict):
    open: str = Field(pattern=SCREEN_NAME)


class FillStep(_Strict):
    fill: str = Field(pattern=FIELD_PATH)    # field widget on the current screen
    value: Value


class TapStep(_Strict):
    tap: str                                 # action/action_button command, or a screen from nav
    row: RowRef | None = None                # list row the action applies to


class ScanStep(_Strict):
    scan: str = Field(pattern=FIELD_PATH)    # scan widget on the current screen
    value: Value


class Expect(_Strict):
    screen: str | None = Field(default=None, pattern=SCREEN_NAME)
    status: str | None = None                # state of the machine shown by the status widget
    error: str | None = None                 # validator/policy hook that rejected the command
    copy_key: str | None = Field(default=None, alias="copy", pattern=COPY_KEY)  # visible text
    visible: list[str] = Field(default_factory=list)                            # visible testids
    row: RowRef | None = None                # this seed row is shown in the list

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    @model_validator(mode="after")
    def _some(self) -> "Expect":
        if not (self.screen or self.status or self.error or self.copy_key or self.visible or self.row):
            raise ValueError("expect: нужна хотя бы одна проверка")
        return self


class ExpectStep(_Strict):
    expect: Expect


def _step_kind(raw: Any) -> str | None:
    keys = raw.keys() if isinstance(raw, dict) else vars(raw).keys()
    return next((k for k in ("open", "fill", "tap", "scan", "expect") if k in keys), None)


Step = Annotated[
    Annotated[OpenStep, Tag("open")] | Annotated[FillStep, Tag("fill")] | Annotated[TapStep, Tag("tap")]
    | Annotated[ScanStep, Tag("scan")] | Annotated[ExpectStep, Tag("expect")],
    Discriminator(_step_kind),
]


class Walk(_Strict):
    role: str
    platform: Platform
    steps: list[Step] = Field(min_length=2)
    covers: list[str] = Field(default_factory=list)     # AC ids checked by this walk


class UiSpec(_Strict):
    schema_version: Literal[1]
    screens: dict[Annotated[str, Field(pattern=SCREEN_NAME)], Screen] = Field(min_length=1)
    menus: dict[str, dict[Platform, list[str]]] = Field(default_factory=dict)
    home: dict[str, dict[Platform, str]] = Field(default_factory=dict)
    walks: dict[Annotated[str, Field(pattern=r"^US-\d{2,}$")], Walk] = Field(default_factory=dict)
    copy_texts: dict[Annotated[str, Field(pattern=COPY_KEY)], str] = Field(default_factory=dict, alias="copy")
    device: dict[Platform, list[DeviceFeature]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    @model_validator(mode="after")
    def _testid_prefix(self) -> "UiSpec":
        for name, screen in self.screens.items():
            prefix = screen_kebab(name) + "."
            for testid in screen.testids():
                if not testid.startswith(prefix):
                    raise ValueError(f"screens.{name}: testid {testid} должен начинаться с {prefix}")
                element = testid.removeprefix(prefix)
                if element == "row" or element.startswith("state-"):
                    raise ValueError(f"screens.{name}: testid {testid} зарезервирован генератором")
        return self


def load_ui(path: str | Path) -> UiSpec:
    return UiSpec.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

"""Answers the ui stage expects from the model (task_class "ui" and "patch")."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts.ui import DeviceFeature, Platform, ScreenState


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoryPlatform(_Strict):
    us: str
    role: str
    platform: Platform


class DropScreen(_Strict):
    role: str
    screen: str


class PlatformPlan(_Strict):
    """Step 1: one platform and performer per user story; base screens a role does not need."""
    stories: list[StoryPlatform]
    drop: list[DropScreen] = Field(default_factory=list)


class PatchOp(_Strict):
    op: Literal["add", "replace", "remove"]
    path: str                      # JSON Pointer into ui.json: /screens/OrderList/pattern
    value: Any = None


class Patch(_Strict):
    """Steps 2 and repair: RFC 6902 subset applied to ui.json."""
    ops: list[PatchOp] = Field(max_length=40)


class Texts(_Strict):
    """Step 4: human texts in meta.lang; unknown screens and keys are ignored."""
    titles: dict[str, str] = Field(default_factory=dict)
    states: dict[str, dict[ScreenState, str]] = Field(default_factory=dict)
    copy_texts: dict[str, str] = Field(default_factory=dict, alias="copy")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Devices(_Strict):
    """Step 5: device capabilities the mobile app needs."""
    features: list[DeviceFeature]

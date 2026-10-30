"""Контракт анализа требований v1 (§3.5 задания)."""

from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

RequirementType = Literal[
    "function", "rule", "data", "interface", "integration", "constraint", "nfr", "goal"
]
IssueCharacteristic = Literal[
    "единичность", "непротиворечивость", "актуальность", "выполнимость",
    "проверяемость", "однозначность", "полнота", "данные",
]
ModuleName = Literal["core", "workflow", "scheduler", "notify"]
PlatformName = Literal["web", "mobile"]
FieldType = Literal[
    "string", "text", "int", "decimal", "money", "bool", "date", "datetime",
    "duration", "interval", "enum", "ref", "state", "geo_point", "geo_line",
    "geo_polygon", "file", "json",
]
SourceId = Annotated[str, StringConstraints(pattern=r"^S-\d{3,}$")]
RequirementId = Annotated[str, StringConstraints(pattern=r"^REQ-\d{2,}$")]
IssueId = Annotated[str, StringConstraints(pattern=r"^ISS-\d{2,}$")]
QuestionId = Annotated[str, StringConstraints(pattern=r"^Q-\d{2,}$")]
AssumptionId = Annotated[str, StringConstraints(pattern=r"^ASM-\d{2,}$")]
StoryId = Annotated[str, StringConstraints(pattern=r"^US-\d{2,}$")]
RuleId = Annotated[str, StringConstraints(pattern=r"^BR-\d{2,}$")]
AcceptanceId = Annotated[str, StringConstraints(pattern=r"^AC-\d{2,}$")]
NfrId = Annotated[str, StringConstraints(pattern=r"^NFR-\d{2,}$")]
Text = Annotated[str, StringConstraints(min_length=1)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)


class Source(ContractModel):
    id: SourceId
    file: Text
    text: str


class Requirement(ContractModel):
    id: RequirementId
    text: Text
    type: RequirementType
    source: list[SourceId]
    quote: str


class Role(ContractModel):
    id: Text
    name: Text
    description: str


class GlossaryEntry(ContractModel):
    term: Text
    definition: Text


class Issue(ContractModel):
    id: IssueId
    req: RequirementId
    characteristic: IssueCharacteristic
    problem: Text
    action: Text


class Question(ContractModel):
    id: QuestionId
    text: Text
    options: list[Text] = Field(min_length=2, max_length=3)
    default: Text
    why: Text
    blocking: bool = False
    answer: str | None = None
    answered_by: Literal["default", "human"] | None = None

    @model_validator(mode="after")
    def validate_options(self) -> Self:
        if len(set(self.options)) != len(self.options):
            raise ValueError("Варианты ответа должны быть уникальными")
        if self.default not in self.options:
            raise ValueError("Ответ по умолчанию должен входить в варианты")
        if (self.answer is None) != (self.answered_by is None):
            raise ValueError("Ответ и его автор должны быть заданы вместе")
        return self


class Assumption(ContractModel):
    id: AssumptionId
    text: Text
    source: Text
    params: dict[str, JsonValue]


class UserStory(ContractModel):
    id: StoryId
    role: Text
    want: Text
    so_that: Text
    req: list[RequirementId]


class RuleParameter(ContractModel):
    type: FieldType
    value: JsonValue


class BusinessRule(ContractModel):
    id: RuleId
    text: Text
    req: list[RequirementId]
    params: dict[str, RuleParameter]


class AcceptanceCriterion(ContractModel):
    id: AcceptanceId
    rules: list[RuleId]
    stories: list[StoryId]
    ui: bool
    gherkin: str


class NonFunctionalRequirement(ContractModel):
    id: NfrId
    text: Text
    metric: str
    verify: str


class OutOfScope(ContractModel):
    req: RequirementId
    reason: Text


class DataCard(ContractModel):
    file: Text
    records: int = Field(ge=0)
    data_schema: dict[str, JsonValue] = Field(alias="schema")
    anomalies: list[JsonValue]
    samples: list[JsonValue]


class Profile(ContractModel):
    modules: list[ModuleName]
    platforms: list[PlatformName]


class Analysis(ContractModel):
    schema_version: Literal[1]
    sources: list[Source]
    requirements: list[Requirement]
    roles: list[Role]
    glossary: list[GlossaryEntry]
    issues: list[Issue]
    questions: list[Question] = Field(max_length=8)
    assumptions: list[Assumption]
    user_stories: list[UserStory]
    rules: list[BusinessRule]
    acceptance: list[AcceptanceCriterion]
    nfr: list[NonFunctionalRequirement]
    out_of_scope: list[OutOfScope]
    data_cards: list[DataCard]
    profile: Profile

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        for name in type(self).model_fields:
            items = getattr(self, name)
            if not isinstance(items, list):
                continue
            counts = Counter(item.id for item in items if hasattr(item, "id"))
            duplicates = sorted(key for key, count in counts.items() if count > 1)
            if duplicates:
                raise ValueError(f"Повторяющиеся id в {name}: {', '.join(duplicates)}")
        return self

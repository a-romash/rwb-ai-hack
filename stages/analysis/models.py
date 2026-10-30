"""Внутренние схемы узких шагов; не меняют общие артефакты."""
from typing import Literal

from pydantic import Field, create_model

from contracts.analysis import (
    AcceptanceCriterion, Assumption, BusinessRule, ContractModel, GlossaryEntry,
    Issue, NonFunctionalRequirement, OutOfScope, Profile, Question, Requirement,
    Role, UserStory,
)


class Extraction(ContractModel):
    requirements: list[Requirement]
    noise: list[str] = Field(default_factory=list)


class Skeleton(ContractModel):
    roles: list[Role]
    glossary: list[GlossaryEntry]
    profile: Profile


class Lint(ContractModel):
    issues: list[Issue]
    questions: list[Question]
    assumptions: list[Assumption]


class Stories(ContractModel):
    user_stories: list[UserStory]


def stories_schema(roles: list[Role]) -> type[ContractModel]:
    if not roles:
        return Stories
    # Ограничивается внутренний ответ шага, общий контракт Analysis не меняется.
    choices = tuple(dict.fromkeys(value for role in roles for value in (role.id, role.name)))
    story = create_model("StoryForDeclaredRole", __base__=UserStory, role=(Literal[choices], ...))
    return create_model("Stories", __base__=ContractModel, user_stories=(list[story], ...))


class Rules(ContractModel):
    rules: list[BusinessRule]


class Acceptance(ContractModel):
    acceptance: list[AcceptanceCriterion]


class Constraints(ContractModel):
    nfr: list[NonFunctionalRequirement]
    out_of_scope: list[OutOfScope]

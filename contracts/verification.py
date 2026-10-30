"""QA artifacts shared with the runner, developer and Studio."""
from typing import Literal
from pydantic import BaseModel, Field

class TestCase(BaseModel):
    id: str
    ac: str | None
    level: Literal['unit','api','rbac','transition','contract','e2e']
    file: str
    status: Literal['passed','failed','skipped','not_run']
    message: str | None = None

class AcStatus(BaseModel):
    specified: bool
    tested: bool
    red_proof: bool | None
    implemented: bool
    passes: bool
    e2e: bool | None
    reason: str | None

class Verification(BaseModel):
    schema_version: Literal[1] = 1
    build: dict[str,bool]
    tests: list[TestCase]
    mutations: list[dict]
    scans: list[dict]
    stand: dict
    ac_status: dict[str,AcStatus]

class Dispute(BaseModel):
    test: str
    ac: str
    reason: str
    hook: str

class DisputeDecision(BaseModel):
    decision: Literal['fix','reject']
    reason: str

class PlannedTest(BaseModel):
    id: str
    ac: str
    file: str
    level: Literal['unit','api','e2e']
    neutral: bool = False
    red_proof: bool | None = None
    failure_kind: Literal['assertion','setup','compile','none','unknown'] = 'unknown'
    lint: list[str] = Field(default_factory=list)

class TestsManifest(BaseModel):
    schema_version: Literal[1] = 1
    tests: list[PlannedTest]
    hashes: dict[str,str]
    acceptance: list[str]
    build_ok: bool

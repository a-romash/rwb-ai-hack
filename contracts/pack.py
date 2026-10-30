"""Product template manifest templates/product/pack.json: trusted commands of the sandbox."""
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image: str | None = None
    env: dict[str, str] | None = None
    restore: list[str] | None = None
    build: list[str] | None = None
    publish: list[str] | None = None
    test: list[str] | None = None
    filter: list[str] | None = None
    reports: dict[str, str] | None = None
    workdir: str | None = None
    e2e: list[str] | None = None
    up: list[str] | None = None
    smoke: list[str] | None = None
    down: list[str] | None = None


class Targets(BaseModel):
    model_config = ConfigDict(extra="forbid")
    backend: Target
    admin: Target
    pwa: Target | None = None
    stack: Target


class Scan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image: str
    commands: list[list[str]]
    reports: dict[str, str] | None = None


class Pack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    targets: Targets
    scan: Scan
    write_roots: list[str]
    readonly: list[str]


PACK = Path(__file__).resolve().parents[1] / "templates" / "product" / "pack.json"


def load_pack(path: str | Path = PACK) -> Pack:
    return Pack.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

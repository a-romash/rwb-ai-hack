"""Экспорт JSON Schema: python -m contracts.export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from contracts.analysis import Analysis
from contracts.app import App


def export_schemas(destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, model in (("analysis", Analysis), ("app", App)):
        schema = model.model_json_schema(by_alias=True, mode="validation")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        path = destination / f"{name}.schema.json"
        path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Экспорт схем контрактов анализа и приложения")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "schemas")
    args = parser.parse_args()
    for path in export_schemas(args.output):
        print(path)


if __name__ == "__main__":
    main()

"""Детерминированные карточки JSON/CSV/GeoJSON без передачи сырых файлов LLM."""
from __future__ import annotations

import csv
import io
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from contracts.analysis import DataCard

MAX_CARD_BYTES = 7000


def _short(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return "[сокращено]"
    if isinstance(value, str):
        return value[:160] + ("…" if len(value) > 160 else "")
    if isinstance(value, dict):
        return {str(key): _short(item, depth + 1) for key, item in list(value.items())[:12]}
    if isinstance(value, list):
        return [_short(item, depth + 1) for item in value[:6]]
    return value


def _kind(value: Any) -> str:
    if value is None or value == "":
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "decimal"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        try:
            int(value)
            return "int"
        except ValueError:
            try:
                float(value)
                return "decimal"
            except ValueError:
                pass
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return "datetime" if "T" in value or " " in value else "date"
        except ValueError:
            pass
    return "string"


def _records(value: Any, path: str = "$") -> tuple[list, str]:
    if isinstance(value, list):
        return value, path
    if isinstance(value, dict):
        if value.get("type") == "FeatureCollection":
            return value.get("features", []), "$.features"
        candidates: list[tuple[list, str]] = []
        for key, item in value.items():
            if isinstance(item, (list, dict)):
                found, location = _records(item, f"{path}.{key}")
                if found:
                    candidates.append((found, location))
        if candidates:
            return max(candidates, key=lambda item: (any(isinstance(row, dict) for row in item[0]), len(item[0])))
        return [value], path
    return [value], path


def _points(coordinates: Any) -> list[tuple[float, float]]:
    if not isinstance(coordinates, list):
        return []
    if len(coordinates) >= 2 and all(isinstance(v, (int, float)) for v in coordinates[:2]):
        return [(float(coordinates[0]), float(coordinates[1]))]
    return [point for child in coordinates for point in _points(child)]


def _line_length(coordinates: Any) -> float:
    if not isinstance(coordinates, list) or not coordinates:
        return 0.0
    if isinstance(coordinates[0], list) and coordinates[0] and isinstance(coordinates[0][0], (int, float)):
        total = 0.0
        for a, b in zip(coordinates, coordinates[1:]):
            lat1, lat2 = math.radians(a[1]), math.radians(b[1])
            dlat, dlon = lat2 - lat1, math.radians(b[0] - a[0])
            h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            total += 6371008.8 * 2 * math.asin(min(1, math.sqrt(h)))
        return total
    return sum(_line_length(child) for child in coordinates)


def profile(path: Path, logical_name: str) -> DataCard:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".csv":
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV не имеет уникальных заголовков")
        records, location = list(reader), "$rows"
    else:
        def reject_constant(value: str) -> None:
            raise ValueError(f"Недопустимое число JSON: {value}")
        records, location = _records(json.loads(text, parse_constant=reject_constant))
    fields: dict[str, list[Any]] = {}
    geometries: list[dict] = []
    rows: list[dict] = []
    for raw in records:
        row = raw if isinstance(raw, dict) else {"value": raw}
        if row.get("type") == "Feature":
            if isinstance(row.get("geometry"), dict):
                geometries.append(row["geometry"])
            row = dict(row.get("properties") or {})
        rows.append(row)
    for key in sorted({key for row in rows for key in row}):
        fields[key] = [row.get(key) for row in rows]
    details: dict[str, Any] = {}
    anomalies: list[Any] = []
    for key, values in fields.items():
        counts = Counter(json.dumps(value, sort_keys=True, ensure_ascii=False) for value in values)
        kinds = Counter(_kind(value) for value in values)
        empty = sum(value is None or value == "" for value in values)
        def is_zero(value: Any) -> bool:
            if isinstance(value, bool) or _kind(value) not in ("int", "decimal"):
                return False
            return float(value) == 0
        zeros = sum(is_zero(value) for value in values)
        info: dict[str, Any] = {
            "types": dict(kinds), "examples": [_short(value) for value in values[:3]],
            "unique": len(counts), "all_unique": len(counts) == len(values),
            "empty": empty, "zeros": zeros,
            "frequent": [{"value": _short(json.loads(value)), "count": count} for value, count in counts.most_common(3)],
        }
        dates = [str(value) for value in values if _kind(value) in ("date", "datetime")]
        if dates:
            try:
                ordered = sorted(dates, key=lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp())
                info["range"] = {"min": ordered[0], "max": ordered[-1]}
            except (ValueError, TypeError, OSError):
                anomalies.append({"field": key, "problem": "Несогласованные часовые пояса или даты"})
        if empty or zeros or len(set(kinds) - {"null"}) > 1:
            anomalies.append({"field": key, "empty": empty, "zeros": zeros, "mixed_types": len(set(kinds) - {"null"}) > 1})
        details[key] = info
    schema: dict[str, Any] = {"records_path": location, "fields": details}
    if geometries:
        points = [p for geometry in geometries for p in _points(geometry.get("coordinates"))]
        lengths = [_line_length(g.get("coordinates")) for g in geometries if g.get("type") in ("LineString", "MultiLineString")]
        schema["geometry"] = {"types": dict(Counter(g.get("type", "unknown") for g in geometries)), "length_unit": "m", "length_method": "haversine_wgs84", "lengths": {"min": min(lengths), "max": max(lengths), "sum": sum(lengths)} if lengths else {}}
        if points:
            schema["geometry"]["bbox"] = [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]
            if any(abs(x) > 180 or abs(y) > 90 for x, y in points):
                anomalies.append("Координаты вне диапазона WGS84")
    card = DataCard(file=logical_name, records=len(records), schema=schema, anomalies=anomalies, samples=[_short(row) for row in rows[:3]])
    # Ограничиваем именно сериализованную карточку, сохраняя имена всех полей.
    if len(card.model_dump_json().encode()) > MAX_CARD_BYTES:
        for info in details.values():
            info.pop("frequent", None)
            info["examples"] = info["examples"][:1]
        card = DataCard(file=logical_name, records=len(records), schema=schema, anomalies=anomalies[:12], samples=[_short(row) for row in rows[:3]])
    if len(card.model_dump_json().encode()) > MAX_CARD_BYTES:
        card.samples = [{key: value[:32] if isinstance(value, str) else value for key, value in sample.items()} for sample in card.samples]
    if len(card.model_dump_json().encode()) > MAX_CARD_BYTES:
        # Широкий файл не теряет поля: вместо потери схемы явно отклоняем его.
        raise ValueError("Карточка слишком широка для профиля окна; разделите набор по группам полей")
    return card

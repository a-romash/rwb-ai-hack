"""Разрешение однозначных подписей в уже объявленные идентификаторы ролей."""
from __future__ import annotations

from contracts.analysis import Role


def role_id(value: str, roles: list[Role]) -> str:
    key = value.strip().casefold()
    matches = {role.id for role in roles if key in (role.id.casefold(), role.name.casefold())}
    return next(iter(matches)) if len(matches) == 1 else value


def normalize_section_roles(section: str, value, roles: list[Role]):
    if section == "roles":
        result = {}
        for key, role in value.items():
            canonical = role_id(key, roles)
            if canonical == key:
                canonical = role_id(role["name"], roles)
            result[canonical] = role
        return result
    if section == "permissions":
        for permission in value:
            permission["role"] = role_id(permission["role"], roles)
    elif section in ("commands", "queries"):
        for operation in value.values():
            operation["roles"] = [role_id(role, roles) for role in operation["roles"]]
    elif section == "state_machines":
        for machine in value.values():
            for transition in machine["transitions"]:
                transition["roles"] = [role_id(role, roles) for role in transition.get("roles", [])]
    elif section == "notifications":
        for notification in value.values():
            notification["to"] = role_id(notification["to"], roles)
    return value

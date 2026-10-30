"""A2: model steps on top of the base ui.json. Every call is one-shot, checked by code, retried once.

1 platforms  — platform and performer per user story, base screens a role does not need
2 refine     — JSON Patch per role: patterns, extra widgets, filters, live, home
3 walks      — one walk per user story, checked by the G1.5 linter
4 texts      — titles, state texts, copy in meta.lang
5 devices    — mobile device capabilities from a closed list
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from contracts.gates import Finding
from contracts.stage import ContractError, ElementFlag, LLM
from contracts.ui import (PATTERN_WIDGETS, REQUIRED_STATES, DeviceFeature, Screen, UiSpec, Walk, screen_kebab)
from gates.g15_ui import check_ui, foreign_text
from stages.ui.appview import AppView
from stages.ui.base import state_texts
from stages.ui.context import app_brief, dumps, screens_brief, story, walk_screens
from stages.ui.llm_io import Devices, Patch, PlatformPlan, StoryPlatform, Texts
from stages.ui.patch import PatchError, apply_patch

AGENTS = Path(__file__).resolve().parents[2] / "agents"
STRUCTURAL = {"UI_REF_UNRESOLVED", "TESTID_DUP", "STATE_MISSING"}
TEXT_CHUNK = 12
AC_ID = re.compile(r"AC-\d+")
FALLBACK_COPY = {
    "ru": {"confirm": "Подтвердите действие", "error": "Действие отклонено. Проверьте данные.", "other": "—"},
    "en": {"confirm": "Please confirm", "error": "The action was rejected. Check the data.", "other": "—"},
}


def system_prompt(agent: str) -> str:
    return (AGENTS / agent / "prompt.md").read_text(encoding="utf-8")


def ask(llm: LLM, agent: str, payload: dict, output: type[BaseModel],
        check: Callable[[Any], list[str]], *, task_class: str = "ui", task_id: str | None = None,
        attempts: int = 2) -> tuple[Any, list[str]]:
    """Call the model; on a schema or check failure retry once with the errors. Returns the last answer."""
    answer, errors = None, []
    for _ in range(attempts):
        user = dumps({**payload, "previous_errors": errors} if errors else payload)
        try:
            candidate = llm(task_class=task_class, system=system_prompt(agent), user=user,
                            output=output, task_id=task_id)
        except ContractError as exc:
            errors = [f"Ответ не прошёл схему: {str(exc).splitlines()[0] if str(exc) else 'ошибка'}"]
            continue
        answer, errors = candidate, check(candidate)
        if not errors:
            break
    return answer, errors


def _lang_key(lang: str) -> str:
    return "ru" if lang.lower().startswith("ru") else "en"


@dataclass
class Builder:
    app_raw: dict
    analysis: dict
    ui: UiSpec
    requirements: str = ""
    plan: dict[str, StoryPlatform] = field(default_factory=dict)
    flags: list[ElementFlag] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def app(self) -> AppView:
        return AppView(self.app_raw)

    @property
    def stories(self) -> list[dict]:
        return list(self.analysis.get("user_stories") or [])

    def findings(self, ui: UiSpec | None = None) -> list[Finding]:
        return check_ui(ui or self.ui, self.app_raw, self.analysis)

    def doc(self) -> dict:
        return self.ui.model_dump(mode="json", by_alias=True, exclude_none=True)

    # --- step 1 --------------------------------------------------------------------------------

    def plan_platforms(self, llm: LLM) -> None:
        stories = self.stories
        if not stories:
            return
        allowed = list((self.analysis.get("profile") or {}).get("platforms") or ["web"])
        allowed = [p for p in allowed if p in ("web", "mobile")] or ["web"]
        roles = {s["id"]: s.get("role") for s in stories}

        def check(plan: PlatformPlan) -> list[str]:
            errors = []
            seen = [s.us for s in plan.stories]
            for us in sorted(set(roles) - set(seen)):
                errors.append(f"Нет платформы для {us}")
            for us in sorted({u for u in seen if seen.count(u) > 1}):
                errors.append(f"У {us} должна быть одна платформа")
            for s in plan.stories:
                if s.us not in roles:
                    errors.append(f"Истории {s.us} нет в анализе")
                elif s.role != roles[s.us]:
                    errors.append(f"Исполнитель {s.us} — {roles[s.us]}, а не {s.role}")
                if s.platform not in allowed:
                    errors.append(f"Платформа {s.platform} не входит в профиль: {', '.join(allowed)}")
            for d in plan.drop:
                if d.screen not in self.ui.screens or d.role not in self.ui.screens[d.screen].roles:
                    errors.append(f"Экрана {d.screen} у роли {d.role} нет")
            return errors

        payload = {"platforms_allowed": allowed,
                   "stories": [{k: s.get(k) for k in ("id", "role", "want", "so_that")} for s in stories],
                   "roles": app_brief(self.app)["roles"],
                   "screens": {n: {"pattern": s.pattern, "roles": s.roles, "title": s.title}
                               for n, s in self.ui.screens.items()}}
        answer, errors = ask(llm, "ux-platforms", payload, PlatformPlan, check, task_id="platforms")
        if answer is None or errors:
            self.notes.append("платформы выбраны по умолчанию")
            self.plan = {s["id"]: StoryPlatform(us=s["id"], role=s.get("role") or "", platform=allowed[0])
                         for s in stories}
            return
        self.plan = {s.us: s for s in answer.stories}
        for d in answer.drop:
            self._drop(d.role, d.screen)
        roles_mobile = {s.role for s in answer.stories if s.platform == "mobile"}
        if roles_mobile:
            self.add_mobile(roles_mobile)

    def _drop(self, role: str, name: str) -> None:
        doc = self.doc()
        screen = doc["screens"][name]
        screen["roles"] = [r for r in screen["roles"] if r != role]
        if not screen["roles"]:
            del doc["screens"][name]
            for other in doc["screens"].values():
                other["nav"] = [n for n in other.get("nav", []) if n != name]
                for action in other.get("actions", []):
                    if action.get("then") == name:
                        action.pop("then")
        for r, platforms in doc.get("menus", {}).items():
            for platform, entries in platforms.items():
                if r == role or name not in doc["screens"]:
                    platforms[platform] = [e for e in entries if e != name]
        for r, platforms in doc.get("home", {}).items():
            for platform, home in list(platforms.items()):
                if home == name and (r == role or name not in doc["screens"]):
                    rest = doc["menus"].get(r, {}).get(platform) or []
                    if rest:
                        platforms[platform] = rest[0]
                    else:
                        del platforms[platform]
        self.ui = UiSpec.model_validate(doc)

    def add_mobile(self, roles: set[str]) -> None:
        """Clone the web screens these roles use into mobile screens (PWA layout, offline state)."""
        doc = self.doc()
        lang = self.app.lang
        web = {n: s for n, s in doc["screens"].items() if s["platform"] == "web" and set(s["roles"]) & roles}
        names = {n: f"Mobile{n}" for n in web if f"Mobile{n}" not in doc["screens"]}
        for name, mobile in names.items():
            screen = dict(web[name])
            old, new = screen_kebab(name) + ".", screen_kebab(mobile) + "."
            retag = lambda item: {**item, "testid": new + item["testid"].removeprefix(old)}
            actions = []
            for action in map(retag, screen.get("actions", [])):
                then = action.pop("then", None)
                if then in names:          # a web-only target is dropped, the action stays
                    action["then"] = names[then]
                actions.append(action)
            screen.update(
                platform="mobile", roles=sorted(set(screen["roles"]) & roles),
                widgets=[retag(w) for w in screen.get("widgets", [])],
                filters=[retag(f) for f in screen.get("filters", [])],
                actions=actions,
                nav=[names[n] for n in screen.get("nav", []) if n in names])
            if screen.get("states") or Screen.model_validate(web[name]).has_data:
                screen["states"] = {**state_texts(lang, "mobile"), **screen.get("states", {})}
            doc["screens"][mobile] = screen
        for role in roles:
            entries = [names[n] for n in doc.get("menus", {}).get(role, {}).get("web", []) if n in names]
            if entries:
                doc.setdefault("menus", {}).setdefault(role, {})["mobile"] = entries[:5]
                doc.setdefault("home", {}).setdefault(role, {})["mobile"] = entries[0]
        doc.setdefault("device", {}).setdefault("mobile", [])
        self.ui = UiSpec.model_validate(doc)

    # --- step 2 --------------------------------------------------------------------------------

    def _structural(self, ui: UiSpec) -> set[tuple[str, str, str]]:
        return {(f.code, f.path, f.message) for f in self.findings(ui)
                if f.severity == "error" and f.code in STRUCTURAL and not f.path.startswith("walks")}

    def try_patch(self, patch: Patch, allowed: Callable[[str], bool]) -> tuple[UiSpec | None, list[str]]:
        bad = [op.path for op in patch.ops if not allowed(op.path)]
        if bad:
            return None, [f"Путь вне зоны шага: {p}" for p in bad]
        try:
            candidate = UiSpec.model_validate(apply_patch(self.doc(), patch.ops))
        except PatchError as exc:
            return None, [f"Патч не применяется: {exc}"]
        except ValidationError as exc:
            return None, [f"После патча ui.json не проходит схему: {e['msg']} в {'.'.join(map(str, e['loc']))}"
                          for e in exc.errors()[:5]]
        new = self._structural(candidate) - self._structural(self.ui)
        return candidate, [f"{code} {path}: {message}" for code, path, message in sorted(new)]

    def refine(self, llm: LLM) -> None:
        for role in sorted(self.app.roles):
            names = [n for n, s in self.ui.screens.items() if role in s.roles]
            if not names:
                continue
            prefixes = ("/copy/", f"/menus/{role}", f"/home/{role}")

            def allowed(path: str, names=names, prefixes=prefixes) -> bool:
                if path.startswith(prefixes):
                    return True
                parts = path.split("/")
                return len(parts) > 2 and parts[1] == "screens" and (parts[2] in names or parts[2] not in self.ui.screens)

            payload = {"role": role, "app": app_brief(self.app),
                       "stories": [s for s in self.stories if s.get("role") == role],
                       "screens": screens_brief(self.ui, names),
                       "menus": self.ui.menus.get(role, {}), "home": self.ui.home.get(role, {}),
                       "pattern_widgets": {p: sorted(w) for p, w in PATTERN_WIDGETS.items()}}
            result: dict[str, UiSpec] = {}

            def check(patch: Patch) -> list[str]:
                candidate, errors = self.try_patch(patch, allowed)
                if candidate is not None and not errors:
                    result["ui"] = candidate
                return errors

            ask(llm, "ux-refine", payload, Patch, check, task_id=f"refine:{role}")
            if "ui" in result:
                self.ui = result["ui"]
            else:
                self.notes.append(f"доработка экранов роли {role} не принята")

    # --- step 3 --------------------------------------------------------------------------------

    def walk_target(self, us: str) -> tuple[str, str]:
        if us in self.plan:
            return self.plan[us].role, self.plan[us].platform
        if us in self.ui.walks:
            return self.ui.walks[us].role, self.ui.walks[us].platform
        role = next((s.get("role") for s in self.stories if s.get("id") == us), "") or ""
        return role, "web" if "web" in self.ui.home.get(role, {}) else "mobile"

    def story_acs(self, us: str) -> set[str]:
        return {a["id"] for a in self.analysis.get("acceptance") or [] if a.get("ui") and us in (a.get("stories") or [])}

    def make_walk(self, llm: LLM, us: str, hints: list[str] | None = None) -> bool:
        role, platform = self.walk_target(us)
        home = self.ui.home.get(role, {}).get(platform)
        if not role or not home:
            self.flags.append(ElementFlag(path=f"walks.{us}", status="questioned", gate="G1.5",
                                          reason=f"У роли {role or '?'} нет главного экрана на платформе {platform}"))
            return False
        acs = self.story_acs(us)
        params = {k: v.get("value") for k, v in self.app.params.items()}
        payload = {"story": story(self.analysis, us), "role": role, "platform": platform, "home": home,
                   "screens": walk_screens(self.ui, role, platform),
                   "seed": app_brief(self.app, with_seed=True)["seed"], "params": params,
                   "states": sorted(self.app.states()),
                   "validators": sorted(h for h, s in self.app.hooks.items() if s.get("kind") in ("validator", "policy")),
                   "copy_keys": sorted(self.ui.copy_texts)}
        if hints:
            payload["gate_findings"] = hints
        result: dict[str, UiSpec] = {}

        def check(walk: Walk) -> list[str]:
            walk = walk.model_copy(update={"role": role, "platform": platform})
            doc = self.doc()
            doc["walks"][us] = walk.model_dump(mode="json", by_alias=True, exclude_none=True)
            for key in _copy_refs(walk):          # texts come in step 4
                doc["copy"].setdefault(key, "")
            candidate = UiSpec.model_validate(doc)
            result["ui"] = candidate
            errors = [f"{f.code} {f.path}: {f.message}" for f in self.findings(candidate)
                      if f.severity == "error" and f.path.startswith(f"walks.{us}")]
            errors += [f"Проход должен покрывать {ac}" for ac in sorted(acs - set(walk.covers))]
            return errors

        _, errors = ask(llm, "ux-walks", payload, Walk, check, task_id=us)
        if "ui" not in result:
            return False
        self.ui = result["ui"]       # keep the last schema-valid walk; G1.5 repair gets another chance
        return not errors

    def make_walks(self, llm: LLM) -> None:
        for s in self.stories:
            if s["id"] not in self.ui.walks:
                self.make_walk(llm, s["id"])

    # --- step 4 --------------------------------------------------------------------------------

    def required_copy(self) -> set[str]:
        keys = set()
        for screen in self.ui.screens.values():
            keys |= {k for w in screen.widgets for k in (w.label, w.group) if k}
            keys |= {a.copy_key for a in screen.actions if a.copy_key}
        for walk in self.ui.walks.values():
            keys |= set(_copy_refs(walk))
        return keys

    def texts(self, llm: LLM) -> None:
        lang = self.app.lang
        rules = {r.get("id"): r.get("text") for r in self.analysis.get("rules") or []}
        hooks = {f"error.{h}": rules.get(s.get("rule"), "") for h, s in self.app.hooks.items()}
        glossary = [g for g in self.analysis.get("glossary") or []][:30]
        names = sorted(self.ui.screens)
        keys = sorted(self.required_copy() | set(self.ui.copy_texts))
        for start in range(0, max(len(names), 1), TEXT_CHUNK):
            chunk = names[start:start + TEXT_CHUNK]
            labels = {e: s.get("label", e) for e, s in self.app.entities.items()}
            payload = {"lang": lang, "glossary": glossary,
                       "screens": {n: {"pattern": self.ui.screens[n].pattern, "title": self.ui.screens[n].title,
                                       "platform": self.ui.screens[n].platform,
                                       "entity": labels.get(_entity(self.ui.screens[n]) or "", ""),
                                       "states": self.ui.screens[n].states} for n in chunk},
                       "copy": {k: self.ui.copy_texts.get(k, "") for k in keys} if start == 0 else {},
                       "rules_for_errors": {k: v for k, v in hooks.items() if k in keys} if start == 0 else {}}

            def check(texts: Texts) -> list[str]:
                found = [t for t in [*texts.titles.values(), *texts.copy_texts.values(),
                                     *(v for s in texts.states.values() for v in s.values())] if foreign_text(t, lang)]
                return [f"Текст не на языке {lang}: {t[:40]}" for t in found]

            answer, _ = ask(llm, "ux-copy", payload, Texts, check, task_id=f"texts:{start // TEXT_CHUNK}")
            if answer is not None:
                self._apply_texts(answer, chunk, keys)
        self._fill_copy()

    def _apply_texts(self, texts: Texts, chunk: list[str], keys: list[str]) -> None:
        lang = self.app.lang
        ok = lambda t: bool(t.strip()) and not foreign_text(t, lang)
        doc = self.doc()
        for name in chunk:
            screen = doc["screens"][name]
            if ok(texts.titles.get(name, "")):
                screen["title"] = texts.titles[name].strip()
            for state, text in (texts.states.get(name) or {}).items():
                if state in REQUIRED_STATES[screen["platform"]] and ok(text):
                    screen.setdefault("states", {})[state] = text.strip()
        for key, text in texts.copy_texts.items():
            if key in keys and ok(text):
                doc["copy"][key] = text.strip()
        self.ui = UiSpec.model_validate(doc)

    def _fill_copy(self) -> None:
        fallback = FALLBACK_COPY[_lang_key(self.app.lang)]
        doc = self.doc()
        for key in self.required_copy():
            if not doc["copy"].get(key, "").strip():
                kind = "error" if key.startswith("error.") else "confirm" if "confirm" in key else "other"
                doc["copy"][key] = fallback[kind]
                self.notes.append(f"текст {key} по умолчанию")
        self.ui = UiSpec.model_validate(doc)

    # --- step 5 --------------------------------------------------------------------------------

    def devices(self, llm: LLM) -> None:
        mobile = {n: s for n, s in self.ui.screens.items() if s.platform == "mobile"}
        if not mobile:
            return
        needed: set[DeviceFeature] = set()
        for screen in mobile.values():
            for widget in screen.widgets:
                if widget.kind == "scan":
                    needed.add("scan_code")
                if widget.kind == "file":
                    needed.add("file_pick")
                if widget.field and (self.app.field(widget.field) or {}).get("type", "").startswith("geo_"):
                    needed.add("location")
        stories = [s for s in self.stories if self.walk_target(s["id"])[1] == "mobile"]
        payload = {"requirements": self.requirements[:6000],
                   "mobile_stories": [{k: s.get(k) for k in ("id", "role", "want")} for s in stories],
                   "notifications": {k: {"on": v.get("on"), "channels": v.get("channels")}
                                     for k, v in (self.app_raw.get("notifications") or {}).items()},
                   "already_needed": sorted(needed)}
        answer, _ = ask(llm, "ux-device", payload, Devices, lambda d: [], task_id="devices")
        if answer is not None:
            needed |= set(answer.features)
        if any("mobile" in (n.get("channels") or []) for n in (self.app_raw.get("notifications") or {}).values()):
            needed.add("local_notification")
        doc = self.doc()
        doc["device"]["mobile"] = sorted(needed)
        self.ui = UiSpec.model_validate(doc)

    # --- repair --------------------------------------------------------------------------------

    def fix_by_code(self, findings: list[Finding]) -> None:
        """Findings that need no model: missing states, duplicated testids."""
        doc = self.doc()
        lang = self.app.lang
        for f in findings:
            if f.code == "STATE_MISSING" and f.path.startswith("screens."):
                screen = doc["screens"].get(f.path.split(".")[1])
                if screen:
                    defaults = state_texts(lang, screen["platform"])
                    screen["states"] = {**defaults, **{k: v for k, v in screen.get("states", {}).items() if v.strip()}}
        seen: set[str] = set()
        for screen in doc["screens"].values():
            for group in ("widgets", "filters", "actions"):
                for item in screen.get(group, []):
                    testid, n = item["testid"], 2
                    while item["testid"] in seen:
                        item["testid"] = f"{testid}-{n}"
                        n += 1
                    seen.add(item["testid"])
        self.ui = UiSpec.model_validate(doc)

    def repair(self, llm: LLM, findings: list[Finding]) -> None:
        self.fix_by_code(findings)
        errors = [f for f in findings if f.severity == "error"]
        walk_hints: dict[str, list[str]] = {}
        for f in errors:
            if f.code == "AC_UI_UNCOVERED":
                for ac in AC_ID.findall(f.message):
                    for s in self.stories:
                        if ac in self.story_acs(s["id"]):
                            walk_hints.setdefault(s["id"], []).append(f.message)
            elif f.path.startswith("walks.US-"):
                walk_hints.setdefault(f.path.split(".")[1], []).append(f"{f.code} {f.path}: {f.message}")
        rest = [f for f in errors if not f.path.startswith("walks") and f.code not in ("STATE_MISSING", "TESTID_DUP")]
        if rest:
            self._repair_patch(llm, rest)
        for us, hints in walk_hints.items():
            if us in {s["id"] for s in self.stories}:
                self.make_walk(llm, us, hints)
        self._fill_copy()

    def _repair_patch(self, llm: LLM, findings: list[Finding]) -> None:
        names = {f.path.split(".")[1] for f in findings if f.path.startswith("screens.")} & set(self.ui.screens)
        payload = {"findings": [f.model_dump() for f in findings], "app": app_brief(self.app),
                   "screens": screens_brief(self.ui, names), "menus": self.ui.menus, "home": self.ui.home,
                   "copy_keys": sorted(self.ui.copy_texts)}
        before = sum(f.severity == "error" for f in self.findings())
        result: dict[str, UiSpec] = {}

        def check(patch: Patch) -> list[str]:
            candidate, errors = self.try_patch(patch, lambda p: p.startswith(("/screens/", "/menus/", "/home/", "/copy/")))
            if candidate is None or errors:
                return errors
            after = sum(f.severity == "error" for f in self.findings(candidate))
            if after >= before:
                return ["Патч не уменьшил число ошибок G1.5"]
            result["ui"] = candidate
            return []

        ask(llm, "ux-refine", payload, Patch, check, task_class="patch", task_id="repair")
        if "ui" in result:
            self.ui = result["ui"]


def _copy_refs(walk: Walk) -> list[str]:
    return [s.expect.copy_key for s in walk.steps if hasattr(s, "expect") and s.expect.copy_key]


def _entity(screen: Screen) -> str | None:
    if screen.source is None:
        return None
    return screen.source.entity or None

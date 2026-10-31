"""Stage tests: acceptance tests of hooks as JSON cases, red-proof on neutral stubs.

The model never writes C#. Cases come from the Examples tables of the criteria; the model only
maps rows to hook inputs when the columns do not match the parameters (stages/tests/cases.py).
The C# side is fixed: a shared data-driven runner in the product template plus one generated
class per criterion that carries the AC trait.
"""
import hashlib
import json

from contracts.stage import ElementFlag, StageOutput, ContractError
from contracts.verification import TestsManifest, PlannedTest
from harness.fakes import workspace_path
from stages.quality import read, write, junit, assertion_failure
from stages.tests import cases as hook_cases
from stages.tests import scenarios as api_scenarios

GENERATED = "product/backend/tests/App.Acceptance.Tests/Generated"


def rule_values(analysis, ac):
    """Parameter values of the criterion's rules (used by the test linter)."""
    ids = set(ac.get('rules', []))
    values = []
    for rule in analysis.get('rules', []):
        if rule.get('id') in ids:
            for value in rule.get('params', {}).values():
                values.append(value.get('value') if isinstance(value, dict) else value)
    return values


def _hooks(workspace, artifacts):
    hooks = read(workspace, artifacts, 'hooks')
    if not isinstance(hooks, list):
        raise ContractError('hooks.json должен быть массивом')
    for hook in hooks:
        # A hook without inputs has an empty list; a missing key means an old scaffold.
        if not hook.get('method') or 'parameters' not in hook:
            raise ContractError(f"В hooks.json нет method/parameters для {hook.get('id')}: обновите scaffold")
    return hooks


def _generate(workspace, analysis, app, hooks, llm, only=None, feedback=None):
    """Write case files and per-criterion classes; returns {ac: [hook ids]} and sources by hook."""
    covered, sources = {}, {}
    for hook in hooks:
        if only is not None and not ({ac['id'] for ac in hook_cases.related(hook, analysis)} & only):
            continue
        previous = []
        if feedback:
            path = workspace_path(workspace, f"{hook_cases.CASES}/{hook['id']}.json")
            previous = json.loads(path.read_text(encoding='utf-8')).get('cases', []) if path.is_file() else []
        found, sources[hook['id']] = hook_cases.build(hook, app, analysis, llm, feedback, previous)
        hook_cases.write(workspace_path, workspace, hook, found)
        for case in found:
            covered.setdefault(case.ac, set()).add(hook['id'])
    for ac in covered:
        path = workspace_path(workspace, f"{GENERATED}/{ac.replace('-', '_')}.cs")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(hook_cases.test_class(ac), encoding='utf-8')
    return covered, sources


def _red_proof(workspace, sandbox, tests):
    """Run each criterion on the neutral stubs: a real test fails on an assertion."""
    for t in tests:
        result = sandbox.run('test', 'backend', filter=t.ac)
        found = junit(workspace, result, [t])
        failed = [c for c in found if c.status == 'failed']
        assertion = any(assertion_failure(c) for c in failed)
        t.failure_kind = 'assertion' if assertion else 'setup' if failed else 'none' if found and all(c.status == 'passed' for c in found) else 'unknown'
        t.red_proof = None if t.neutral else assertion


def execute(inp, workspace, llm, sandbox):
    workspace = workspace.resolve()
    analysis = read(workspace, inp.artifacts, 'analysis')
    app = read(workspace, inp.artifacts, 'app')
    hooks = _hooks(workspace, inp.artifacts)
    # Neutral stubs are kept for the dispute red-proof; the hook bodies are not shown to QA.
    stubs = {}
    for hook in hooks:
        target = workspace_path(workspace, 'product/' + hook['file'])
        if target.is_file():
            stubs[hook['id']] = {'file': 'product/' + hook['file'], 'source': target.read_text(encoding='utf-8')}
    write(workspace, 'reports/redproof-stubs.json', stubs)
    covered, sources = _generate(workspace, analysis, app, hooks, llm)
    # API scenarios exercise code the generator wrote, so they pass on the stubs: neutral for red-proof
    # unless the criterion also has hook cases.
    flows = api_scenarios.build(app, analysis)
    for ac, found in flows.items():
        api_scenarios.write(workspace_path, workspace, ac, found)
    tests = []
    for ac in sorted(set(covered) | set(flows)):
        ident = ac.replace('-', '_')
        neutral = next((a.get('neutral_expectation', False) for a in analysis['acceptance'] if a['id'] == ac), False)
        if ac in covered:
            tests.append(PlannedTest(id=ac, ac=ac, file=f"{GENERATED}/{ident}.cs", level='unit', neutral=neutral))
        else:
            tests.append(PlannedTest(id=ac, ac=ac, file=f"{GENERATED}/{ident}_Scenario.cs", level='api', neutral=True))
    from stages.tests.e2e import generate
    e2e, skipped = generate(workspace, read(workspace, inp.artifacts, 'ui', optional=True), app)
    build = sandbox.run('build', 'backend')
    manifest = TestsManifest(tests=tests, hashes={}, acceptance=[a['id'] for a in analysis.get('acceptance', [])], build_ok=build.ok)
    if build.ok:
        _red_proof(workspace, sandbox, tests)
    else:
        for t in tests:
            t.failure_kind = 'compile'
    save(workspace, manifest)
    write(workspace, 'reports/test-cases.json', {'schema_version': 1, 'sources': sources, 'e2e': e2e,
                                                 'covered': {ac: sorted(ids) for ac, ids in covered.items()},
                                                 'scenarios': {ac: [x['id'] for x in found] for ac, found in flows.items()}})
    return StageOutput(artifacts={'tests': 'reports/tests.json'},
                       flags=[ElementFlag(path=f"ui.walks.{ident}", status='questioned', reason=f"E2E-проход не собран: {reason}")
                              for ident, reason in skipped.items()],
                       summary=f"Тесты для {len(tests)} из {len(manifest.acceptance)} AC "
                               f"(сценариев API: {sum(map(len, flows.values()))}); E2E-проходов: {len(e2e)}")


def save(workspace, manifest):
    manifest.hashes = {}
    for directory in ('product/backend/tests', 'product/admin-web/e2e', 'product/mobile-web/e2e'):
        root = workspace_path(workspace, directory)
        if root.exists():
            for path in sorted(root.rglob('*')):
                if path.is_file() and not any(part in ('bin', 'obj', 'node_modules') for part in path.parts):
                    relative = str(path.relative_to(workspace))
                    workspace_path(workspace, relative)
                    manifest.hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    for relative in ('product/admin-web/playwright.config.ts', 'product/mobile-web/playwright.config.ts',
                     'product/admin-web/jest.config.cjs', 'product/mobile-web/jest.config.cjs'):
        path = workspace_path(workspace, relative)
        if path.is_file():
            manifest.hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    write(workspace, 'reports/tests.json', manifest.model_dump())


def repair(inp, workspace, llm, findings, *, sandbox=None):
    """G2 findings: ask again for the cases of the affected criteria and repeat the red-proof."""
    if sandbox is None:
        raise ContractError('Для repair требуется песочница')
    workspace = workspace.resolve()
    data = TestsManifest.model_validate(read(workspace, {'tests': 'reports/tests.json'}, 'tests'))
    analysis = read(workspace, inp.artifacts, 'analysis')
    app = read(workspace, inp.artifacts, 'app')
    hooks = _hooks(workspace, inp.artifacts)
    affected = {f.path.removeprefix('tests/') for f in findings} & set(data.acceptance)
    feedback = {}
    for f in findings:
        feedback.setdefault(f.path.removeprefix('tests/'), []).append(f"{f.code}: {f.message}")
    covered, _ = _generate(workspace, analysis, app, hooks, llm, only=affected, feedback=feedback)
    known = {t.ac for t in data.tests}
    for ac in sorted(set(covered) - known):
        data.tests.append(PlannedTest(id=ac, ac=ac, file=f"{GENERATED}/{ac.replace('-', '_')}.cs", level='unit'))
    build = sandbox.run('build', 'backend')
    data.build_ok = build.ok
    if build.ok:
        _red_proof(workspace, sandbox, [t for t in data.tests if t.ac in affected])
    save(workspace, data)
    return StageOutput(artifacts={'tests': 'reports/tests.json'}, summary='Кейсы пересобраны по находкам G2')

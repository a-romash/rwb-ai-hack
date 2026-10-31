"""Run stage-owned gate checks and bounded repairs without taking ownership of them."""
import importlib
from pathlib import Path

from contracts.gates import Finding, GateResult
from contracts.stage import ContractError, StageInput, StageOutput

MODULES = {
    "G0": "gates.g0_inputs", "G1": "gates.g1_spec", "G1.5": "gates.g15_ui",
    "G2": "gates.g2_redproof", "G3": "gates.g3_checks", "G4": "gates.g4_stand",
    "G5": "gates.g5_docs",
}


def check_gate(gate: str, workspace: Path, artifacts: dict[str, str], *, allow_missing: bool = False) -> GateResult:
    name = MODULES[gate]
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name or not allow_missing:
            raise ContractError(f"Обязательный гейт {gate} недоступен") from exc
        return GateResult(gate=gate, passed=True, findings=[Finding(path="", code="GATE_MISSING", severity="warning", message=f"Гейт {gate} не подключён")])
    result = GateResult.model_validate(module.check(workspace, artifacts))
    if result.gate != gate or result.passed != (not any(f.severity == "error" for f in result.findings)):
        raise ContractError(f"Некорректный результат гейта {gate}")
    return result


def run_gate(gate, module, inp: StageInput, workspace: Path, llm, output: StageOutput, *, allow_missing=False, sandbox=None):
    """Return latest output and the complete sequence of results (round 0..2)."""
    results = []
    for round_number in range(3):
        result = check_gate(gate, workspace, {**inp.artifacts, **output.artifacts}, allow_missing=allow_missing)
        results.append(result)
        errors = [f for f in result.findings if f.severity == "error"]
        if any(f.code.startswith("CONTRACT_") for f in errors):
            raise ContractError(f"Нарушен контракт гейта {gate}")
        if not errors or round_number == 2 or not hasattr(module, "repair"):
            break
        import inspect
        parameters = inspect.signature(module.repair).parameters
        kwargs = {'sandbox': sandbox} if 'sandbox' in parameters else {}
        if 'previous_output' in parameters:
            kwargs['previous_output'] = output
        output = StageOutput.model_validate(module.repair(inp, workspace, llm, errors, **kwargs))
    return output, results

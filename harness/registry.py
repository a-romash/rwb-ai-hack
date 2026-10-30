"""Fixed sequential pipeline; importing this does not import real stages."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    key: str
    module: str
    deps: tuple[str, ...]
    queue: str
    gates: tuple[str, ...]
    title: str
    rwb_stage: str
    participants: tuple[str, ...]
    always: bool = False


STAGES = (
    Stage("analysis", "stages.analysis", (), "llm", ("G0",), "Анализ требований", "Э1", ("business_analysis",)),
    Stage("spec", "stages.spec", ("analysis",), "llm", ("G1",), "Системный анализ", "Э2", ("system_analysis", "database")),
    Stage("ui", "stages.ui", ("spec",), "llm", ("G1.5",), "Интерфейсы", "Э3", ("interfaces",)),
    Stage("scaffold", "stages.scaffold", ("ui",), "build", (), "Каркас приложения", "Э4", ("frontend", "backend", "database", "cicd")),
    Stage("tests", "stages.tests", ("scaffold",), "build", ("G2",), "Тесты приёмки", "Э5", ("testing",)),
    Stage("develop", "stages.develop", ("tests",), "build", (), "Разработка", "Э4", ("backend", "frontend")),
    Stage("verify", "stages.verify", ("develop",), "build", ("G3", "G4"), "Проверки и стенд", "Э5–Э6", ("testing", "security", "cicd")),
    Stage("report", "stages.report", ("verify",), "llm", ("G5",), "Отчёт", "Э7", ("documentation",), always=True),
)
STAGES_BY_KEY = {stage.key: stage for stage in STAGES}

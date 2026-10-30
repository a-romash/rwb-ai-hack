# Этапы качества

`tests`, `verify`, `report` используют общий `StageInput → StageOutput`, LLM и Sandbox.
Гейты G2–G5 читают сохранённые артефакты и не запускают инструменты.

## Независимая проверка

Из корня репозитория:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s tests -v
uv pip install --python backend/.venv/bin/python -r backend/requirements-quality.txt
PYTHONPATH=. backend/.venv/bin/python scripts/quality_smoke.py --mkdocs
# Расходует ключ из .env:
PYTHONPATH=. backend/.venv/bin/python scripts/quality_smoke.py --live --mkdocs
```

Фикстуры двух доменов находятся в `contracts/fixtures/tickets` и `equipment`.
`tests/fixtures/quality-product` — отдельный C#-продукт для проверки границ 4/5/6;
он не входит в генерируемое приложение и не содержит модели.

## Условия интеграции

- Иван предоставляет TestKit, сигнатуры хуков и команды backend/admin/pwa в pack.yaml.
- JUnit должен содержать свойство `AC` или ID AC в имени класса/теста.
- Отчёты сканеров передаются в SandboxResult.reports (sarif/json); Playwright — json.
- UI-проходы требуют явных маршрутов screen.route и testid для проверок/ввода.
  Неизвестный маршрут/селектор не угадывается, а отклоняется.
- QA не получает тела хуков. Снимок нейтральных заглушок хранится в reports/redproof-stubs.json
  только для повторного red-proof спора, не передаётся в LLM.
- Спор сохраняется в reports/disputes.json. Принятие нового хэша платформой — отдельная
  доверенная интеграция с approve_test_change; изменение манифеста само по себе не даёт такого права.
- Отсутствие машинного отчёта не считается успехом. Ошибка сборки мутанта не считается убийством.

## Ограничения текущей интеграции

Проверки Python и live-writer не заменяют настоящий прогон продукта. Требуются
подготовленные образы .NET/Node/security, TestKit, PWA и машинные отчёты из ветки Ивана.
Проверка роли в smoke зависит от отчёта реализации smoke; один HTTP 200 не доказывает RBAC.

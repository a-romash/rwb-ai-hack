# Оценка analysis/spec

Режим: `live`. Дата UTC: 2026-10-30T13:07:37.558536+00:00.

Записанные ответы не являются прогоном настоящей модели; неизвестные метрики обозначены `—`.

| Кейс | Статус | REQ | Цитаты | ISS / Q | BR с AC | G1 до → после | Вызовы | Токены |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| equipment | partial | 9 | 1.0 | 10 / 3 | 1.0 | 43 → 42 | 79 | 164365 |

## equipment

Статус: `partial`. Время: 502081 мс.

Артефакты и сырые выходы модели: `workspaces/eval/20261030T125915470114/equipment`.

Находки после ремонта:

- `REF_UNRESOLVED` `analysis.assumptions[ASM-07]`: Ссылка «Все требования» не разрешается.
- `REF_UNRESOLVED` `entities.Equipment.owner`: Ссылка «EquipmentRegistry» не разрешается.
- `REF_UNRESOLVED` `entities.Equipment.fields.type`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `entities.Equipment.fields.type`: Ссылка «EquipmentType» не разрешается.
- `REF_UNRESOLVED` `entities.Employee.owner`: Ссылка «EmployeeRegistry» не разрешается.
- `REF_UNRESOLVED` `entities.EquipmentOperation.owner`: Ссылка «EquipmentRegistry» не разрешается.
- `REF_UNRESOLVED` `entities.EquipmentOperation.fields.operation_type`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `entities.EquipmentOperation.fields.operation_type`: Ссылка «OperationType» не разрешается.
- `REF_UNRESOLVED` `hooks.can_issue_equipment.rule`: Ссылка «Оборудование должно иметь статус 'available'. Если тип оборудования 'laptop', количество выданных ноутбуков сотруднику должно быть строго меньше max_laptops_per_employee.» не разрешается.
- `REF_UNRESOLVED` `hooks.can_issue_equipment.select`: Ссылка «SELECT COUNT(*) FROM Equipment WHERE current_holder = :employee_id AND type = 'laptop' AND status = 'issued'» не разрешается.
- `REF_UNRESOLVED` `hooks.can_create_equipment.rule`: Ссылка «Инвентарный номер оборудования должен быть уникальным в системе. Тип оборудования должен быть одним из допустимых значений (ноутбук, другое).» не разрешается.
- `REF_UNRESOLVED` `commands.create_equipment.input.type`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `commands.create_equipment.input.type`: Ссылка «EquipmentType» не разрешается.
- `REF_UNRESOLVED` `commands.issue_equipment.input.equipment_id`: Ссылка «scan_qr» не разрешается.
- `REF_UNRESOLVED` `commands.issue_equipment.input.employee_id`: Ссылка «scan_qr» не разрешается.
- `REF_UNRESOLVED` `commands.return_equipment.input.employee_id`: Ссылка «scan_qr_code» не разрешается.
- `BR_NO_HOOK` `hooks`: Правило BR-01 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-02 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-03 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-04 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-05 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-06 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-07 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-08 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-09 не представлено хуком или декларативным правилом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-05]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `RBAC_ORPHAN` `permissions`: Роль operator не имеет права выполнять команду create_equipment.
- `RBAC_ORPHAN` `permissions`: Роль operator не имеет права выполнять команду issue_equipment.
- `RBAC_ORPHAN` `permissions`: Роль operator не имеет права выполнять команду return_equipment.
- `RBAC_ORPHAN` `permissions`: Роль employee не имеет права выполнять команду get_my_equipment.
- `RBAC_ORPHAN` `permissions`: Роль employee не имеет права выполнять команду get_my_equipment_history.
- `RBAC_ORPHAN` `permissions`: Роль operator не имеет права выполнять команду get_all_equipment.
- `RBAC_ORPHAN` `permissions`: Роль operator не имеет права выполнять команду get_all_equipment_history.
- `US_NO_ENDPOINT` `analysis.user_stories[US-01]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-02]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-03]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-04]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-05]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-06]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-07]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-08]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-09]`: История не связана с доступной своей роли операцией API.

Честных флагов сомнения/зависимости: 398.

## Версии промптов

Версия указана в каждой карточке и config.yaml; SHA-256 фиксирует точный текст:

- `analyst-acceptance`: `2f254f76fe172ca28d3ceb144aea2043a6168ac82d588818668329caf3d41e9d`
- `analyst-constraints`: `3705cc4b7e2e82431836d77628726cc1467136f25f40691529c648df1f2ac35b`
- `analyst-domain`: `7cb828957d863713df0d9f94dd4286e8493aeeb45c37ed5a12f960dddd5596ab`
- `analyst-extract`: `e3b53b90ed84aa45a23a9d75ae191202fa2abe4e224263e6685493c769fb2a2c`
- `analyst-lint`: `0407360f28e1d360b46989f4b3acab0b01f34358ece164c9a201f16c3cfec831`
- `analyst-repair`: `2deaffe3084c84bfd794a4f9ac3a6ce584844afc43e032a8f57049f52d44f34f`
- `analyst-rules`: `6b72cac258ee1b316600732c867c66acd7fa61b6854fbe3810c8567f166e55b6`
- `analyst-stories`: `64a09c0f17e945292946008c9b18ea7008d6bb159adc3c554b26ed1731e2ad00`
- `system-analyst-access`: `20f2b511198144199464bef316f8a46eeeda0a9f6c684660ccc37d7ba7a7f6d4`
- `system-analyst-api`: `2aabad19780d43635b7681f0453fa3a466bff40b8bb1d2e2ce7a635ff949bb40`
- `system-analyst-behavior`: `6846328fe871b1e9d4972fc14f3f322f6b2c86cb11a480faf04be45476520c48`
- `system-analyst-data`: `51bf3a18bab6192a55c1f62be360e693f1d6cf8e06ca060be4c524c56df9117a`
- `system-analyst-domain`: `ae4ad99aa6c56da5f71cb363fec90719576b67cd9b7b6c3fafa84dcd2889a4fa`
- `system-analyst-environment`: `8c39e550309ae6699cfb08a6cfba7613fcc06e5e5de5e6c736a9fb3a02de92e7`
- `system-analyst-repair`: `a70ccfdd9d918fb0e50e44cd7d0b9ff54f19fa7afa977bb31d889107c924debe`
- `system-analyst-rules`: `2fbd8057ed41ec79209c6d186fcb9b05813810400e2def491c93a004567dfda5`

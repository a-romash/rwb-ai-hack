# Оценка analysis/spec

Режим: `live`. Дата UTC: 2026-10-30T13:15:07.735094+00:00.

Записанные ответы не являются прогоном настоящей модели; неизвестные метрики обозначены `—`.

| Кейс | Статус | REQ | Цитаты | ISS / Q | BR с AC | G1 до → после | Вызовы | Токены |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| tickets | partial | 18 | 1.0 | 7 / 4 | 1.0 | 78 → 78 | 107 | 302380 |

## tickets

Статус: `partial`. Время: 952267 мс.

Артефакты и сырые выходы модели: `/home/haus/Projects/rwb-ai-hack/workspaces/eval/20261030T125915462885/tickets`.

Находки после ремонта:

- `REF_UNRESOLVED` `analysis.assumptions[ASM-01]`: Ссылка «BR-20» не разрешается.
- `REF_UNRESOLVED` `entities.RepairRequest.owner`: Ссылка «office_employee» не разрешается.
- `REF_UNRESOLVED` `entities.OfficeEmployee.owner`: Ссылка «office_employee» не разрешается.
- `REF_UNRESOLVED` `entities.Engineer.owner`: Ссылка «engineer» не разрешается.
- `REF_UNRESOLVED` `entities.Dispatcher.owner`: Ссылка «dispatcher» не разрешается.
- `REF_UNRESOLVED` `state_machines.RepairRequestStatus.transitions[2].guard`: Ссылка «has_resolution» не разрешается.
- `REF_UNRESOLVED` `state_machines.RepairRequestStatus.transitions[3].guard`: Ссылка «is_deadline_passed» не разрешается.
- `REF_UNRESOLVED` `state_machines.RepairRequestStatus.transitions[3].trigger.schedule`: Ссылка «overdue_check_interval» не разрешается.
- `REF_UNRESOLVED` `state_machines.RepairRequestStatus.transitions[5].guard`: Ссылка «has_resolution» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_topic_length.rule`: Ссылка «Длина поля «тема» (RepairRequest.subject) не превышает 255 символов.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_description_length.rule`: Ссылка «Длина поля «описание» (RepairRequest.description) не превышает 2000 символов.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_priority.rule`: Ссылка «Значение поля «приоритет» входит в список допустимых значений priority_values.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_resolution_required.rule`: Ссылка «Поле «решение» должно быть заполнено (не пустое) при закрытии заявки.» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_deadline.rule`: Ссылка «Рассчитать срок решения заявки на основе приоритета, времени создания и рабочего времени. Если заявка создана вне рабочего времени, отсчет начинается с начала следующего рабочего дня (work_start_time).» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_deadline.in`: Ссылка «current_time» не разрешается.
- `REF_UNRESOLVED` `hooks.check_overdue.rule`: Ссылка «Определить, истек ли срок решения заявки (current_time > deadline).» не разрешается.
- `REF_UNRESOLVED` `hooks.check_overdue.in`: Ссылка «current_time» не разрешается.
- `REF_UNRESOLVED` `hooks.mark_request_overdue.rule`: Ссылка «Если заявка просрочена (is_overdue = true) и статус не «закрыта», изменить статус на «просроченная».» не разрешается.
- `REF_UNRESOLVED` `hooks.notify_dispatcher_overdue.rule`: Ссылка «При переходе заявки в состояние «просроченная» создать внутреннее уведомление для диспетчера с идентификатором заявки.» не разрешается.
- `REF_UNRESOLVED` `hooks.notify_dispatcher_overdue.in`: Ссылка «RepairRequest.id» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_open_requests_count.rule`: Ссылка «Подсчитать количество заявок со статусом «новая» или «в работе».» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_open_requests_count.out`: Ссылка «dashboard_open_count» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_open_requests_count.select`: Ссылка «select_open_requests» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_overdue_requests_count.rule`: Ссылка «Подсчитать количество заявок со статусом «просроченная».» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_overdue_requests_count.out`: Ссылка «dashboard_overdue_count» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_overdue_requests_count.select`: Ссылка «select_overdue_requests» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_avg_resolution_time.rule`: Ссылка «Рассчитать среднее время решения (resolved_at - created_at) по закрытым заявкам, закрытым за последние avg_resolution_period.» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_avg_resolution_time.out`: Ссылка «dashboard_avg_resolution_time» не разрешается.
- `REF_UNRESOLVED` `hooks.calculate_avg_resolution_time.select`: Ссылка «select_closed_requests_in_period» не разрешается.
- `REF_UNRESOLVED` `hooks.filter_engineer_requests.rule`: Ссылка «Показать инженеру только заявки, где assigned_engineer равен current_user_id.» не разрешается.
- `REF_UNRESOLVED` `hooks.filter_engineer_requests.in`: Ссылка «current_user_id» не разрешается.
- `REF_UNRESOLVED` `hooks.filter_queue_requests.rule`: Ссылка «Показать в общей очереди только заявки со статусом «новая».» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_request_creation.rule`: Ссылка «Сотрудник офиса (office_employee) имеет право создавать заявки на ремонт, указывая тему, описание и приоритет.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_request_creation.in`: Ссылка «current_user_id» не разрешается.
- `REF_UNRESOLVED` `commands.create_repair_request.effects`: Ссылка «new» не разрешается.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-08]`: У порога правила BR-08 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-09]`: У порога правила BR-09 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-10]`: У порога правила BR-10 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-08]`: У порога правила BR-11 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-16]`: У порога правила BR-17 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-20]`: У порога правила BR-21 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-08]`: У порога правила BR-22 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-21]`: У порога правила BR-23 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-16]`: У порога правила BR-25 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_HOOK` `hooks`: Правило BR-01 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-02 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-03 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-04 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-05 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-06 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-07 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-08 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-09 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-10 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-11 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-12 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-13 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-14 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-15 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-16 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-17 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-18 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-19 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-20 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-21 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-22 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-23 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-24 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-25 не представлено хуком или декларативным правилом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-02]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-03]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-20]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-21]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `RBAC_ORPHAN` `permissions`: Роль engineer не имеет права выполнять команду take_request.
- `RBAC_ORPHAN` `permissions`: Роль engineer не имеет права выполнять команду close_request.
- `RBAC_ORPHAN` `permissions`: Роль engineer не имеет права выполнять команду return_to_queue.
- `RBAC_ORPHAN` `commands.check_overdue.roles`: У команды отсутствует роль.
- `RBAC_ORPHAN` `analysis.user_stories[US-10]`: Роль истории не может выполнить связанное действие.

Честных флагов сомнения/зависимости: 1137.

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

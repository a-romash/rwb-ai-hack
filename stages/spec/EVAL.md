# Оценка analysis/spec

Режим: `live`. Дата UTC: 2026-10-30T14:07:31.218022+00:00.

Записанные ответы не являются прогоном настоящей модели; неизвестные метрики обозначены `—`.

| Кейс | Статус | REQ | Цитаты | ISS / Q | BR с AC | G1 до → после | Вызовы | Токены |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| tickets | partial | 18 | 1.0 | 7 / 4 | 1.0 | 75 → 75 | 107 | 302380 |
| equipment | partial | 9 | 1.0 | 10 / 3 | 1.0 | 42 → 41 | 79 | 164365 |
| case1 | partial | 28 | 1.0 | 8 / 5 | 1.0 | 86 → 86 | 87 | 278694 |

## tickets

Статус: `partial`. Время: 952267 мс.

Артефакты и сырые выходы модели: `workspaces/eval/20261030T125915462885/tickets`.

Чистые гейты повторены после уточнения Gherkin Examples/единиц; артефакты и вызовы модели не менялись. Счётчики G1 до и после вычислены одной текущей версией валидаторов.

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
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-20]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `RBAC_ORPHAN` `permissions`: Роль engineer не имеет права выполнять команду take_request.
- `RBAC_ORPHAN` `permissions`: Роль engineer не имеет права выполнять команду close_request.
- `RBAC_ORPHAN` `permissions`: Роль engineer не имеет права выполнять команду return_to_queue.
- `RBAC_ORPHAN` `commands.check_overdue.roles`: У команды отсутствует роль.
- `RBAC_ORPHAN` `analysis.user_stories[US-10]`: Роль истории не может выполнить связанное действие.

Честных флагов сомнения/зависимости: 1072.

## equipment

Статус: `partial`. Время: 502081 мс.

Артефакты и сырые выходы модели: `workspaces/eval/20261030T125915470114/equipment`.

Чистые гейты повторены после уточнения Gherkin Examples/единиц; артефакты и вызовы модели не менялись. Счётчики G1 до и после вычислены одной текущей версией валидаторов.

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

Честных флагов сомнения/зависимости: 360.

## case1

Статус: `partial`. Время: 653286 мс.

Артефакты и сырые выходы модели: `workspaces/eval/20261030T134031308295/case1`.

Чистые гейты повторены после уточнения Gherkin Examples/единиц; артефакты и вызовы модели не менялись. Счётчики G1 до и после вычислены одной текущей версией валидаторов.

После исправления обработки окна выполнен только второй круг ремонта над сохранёнными артефактами. Все прежние вызовы и токены учтены; незаписанные изменения прерванного первого круга потеряны. Исходный неуспешный отчёт сохранён.

Исходный сбой: `contract_error` — Контекст запроса превышает профиль окна.

Находки после ремонта:

- `REF_UNRESOLVED` `analysis.assumptions[ASM-01]`: Ссылка «REQ-15, REQ-22» не разрешается.
- `REF_UNRESOLVED` `entities.ParkingZone.owner`: Ссылка «admin» не разрешается.
- `REF_UNRESOLVED` `entities.ParkingSession.owner`: Ссылка «driver» не разрешается.
- `REF_UNRESOLVED` `entities.ParkingSession.fields.status`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `entities.Vehicle.owner`: Ссылка «driver» не разрешается.
- `REF_UNRESOLVED` `entities.PaymentAdapter.owner`: Ссылка «admin» не разрешается.
- `REF_UNRESOLVED` `state_machines.ParkingSession.transitions[1].trigger.timer`: Ссылка «warning_lead_time» не разрешается.
- `REF_UNRESOLVED` `state_machines.ParkingSession.transitions[2].trigger.timer`: Ссылка «session_end_time» не разрешается.
- `REF_UNRESOLVED` `hooks.determine_zone_membership.rule`: Ссылка «Определяет, находится ли точка Vehicle.location внутри полигона ParkingZone.boundary, используя координатную систему coordinate_system.» не разрешается.
- `REF_UNRESOLVED` `hooks.determine_zone_membership.out`: Ссылка «boolean» не разрешается.
- `REF_UNRESOLVED` `hooks.determine_zone_membership.select`: Ссылка «select ParkingZone from PostGIS_test_data» не разрешается.
- `REF_UNRESOLVED` `hooks.display_zone_info_on_entry.rule`: Ссылка «При событии въезда в зону отображает номер зоны, её границы и доступные параметры парковки в пользовательском интерфейсе.» не разрешается.
- `REF_UNRESOLVED` `hooks.store_session_times.rule`: Ссылка «Проверяет наличие времени начала и окончания сессии, где время окончания получено от источника session_end_time_source.» не разрешается.
- `REF_UNRESOLVED` `hooks.detect_zone_exit.rule`: Ссылка «Определяет, переместилась ли точка Vehicle.location за пределы полигона текущей зоны ParkingSession.zone.boundary.» не разрешается.
- `REF_UNRESOLVED` `hooks.detect_zone_exit.in`: Ссылка «ParkingSession.zone.boundary» не разрешается.
- `REF_UNRESOLVED` `hooks.detect_zone_exit.out`: Ссылка «boolean» не разрешается.
- `REF_UNRESOLVED` `hooks.detect_zone_transition.rule`: Ссылка «Определяет, переместилась ли точка Vehicle.location в границы другой зоны ParkingZone.boundary, отличной от текущей.» не разрешается.
- `REF_UNRESOLVED` `hooks.detect_zone_transition.select`: Ссылка «select ParkingZone from PostGIS_test_data» не разрешается.
- `REF_UNRESOLVED` `hooks.check_session_warning.rule`: Ссылка «Формирует предупреждение, если разница между ParkingSession.endTime и current_time меньше или равна warning_lead_time.» не разрешается.
- `REF_UNRESOLVED` `hooks.check_session_warning.in`: Ссылка «current_time» не разрешается.
- `REF_UNRESOLVED` `hooks.check_session_warning.out`: Ссылка «boolean» не разрешается.
- `REF_UNRESOLVED` `hooks.generate_payment_deep_link.rule`: Ссылка «Формирует deep link с параметрами текущей сессии для перехода к официальному сервису оплаты.» не разрешается.
- `REF_UNRESOLVED` `hooks.generate_payment_deep_link.in`: Ссылка «ParkingSession.zone.zoneNumber» не разрешается.
- `REF_UNRESOLVED` `hooks.display_session_history.rule`: Ссылка «Отображает список завершённых парковочных сессий и маршрут перемещений в пользовательском интерфейсе.» не разрешается.
- `REF_UNRESOLVED` `hooks.display_session_history.in`: Ссылка «ParkingSession.zone.zoneNumber» не разрешается.
- `REF_UNRESOLVED` `hooks.invoke_payment_adapter.rule`: Ссылка «Обеспечивает вызов методов адаптера (getZoneInfo, startSession, endSession, getSessionStatus) через REST API для управления сессией.» не разрешается.
- `REF_UNRESOLVED` `hooks.enforce_no_internal_payment.rule`: Ссылка «Запрещает использование собственного платежного механизма и требует промышленного доступа к платежным системам.» не разрешается.
- `REF_UNRESOLVED` `hooks.handle_gps_error.rule`: Ссылка «При недоступности сигнала GPS отображает сообщение об ошибке и блокирует формирование событий въезда в зону.» не разрешается.
- `REF_UNRESOLVED` `hooks.handle_network_error.rule`: Ссылка «При потере соединения с сетью отображает сообщение об ошибке и сохраняет данные сессии локально для повторной отправки.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_zone_count.rule`: Ссылка «Проверяет, что количество платных зон в тестовых данных находится в диапазоне от min_zones_count до max_zones_count.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_zone_count.out`: Ссылка «boolean» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_zone_count.select`: Ссылка «select ParkingZone from PostGIS_test_data» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_documentation.rule`: Ссылка «Проверяет наличие документации в форматах Markdown и PDF, включающей системную, продуктовую и пользовательскую части.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_documentation.in`: Ссылка «doc_files» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_documentation.out`: Ссылка «boolean» не разрешается.
- `REF_UNRESOLVED` `commands.start_session.effects`: Ссылка «start_session» не разрешается.
- `REF_UNRESOLVED` `commands.end_session.effects`: Ссылка «end_session» не разрешается.
- `REF_UNRESOLVED` `commands.cancel_session.effects`: Ссылка «cancel_session» не разрешается.
- `REF_UNRESOLVED` `commands.monitor_events.input.status`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `permissions[6].op`: Операция права доступа не существует.
- `REF_UNRESOLVED` `permissions[17].op`: Операция права доступа не существует.
- `REF_UNRESOLVED` `permissions[18].op`: Операция права доступа не существует.
- `REF_UNRESOLVED` `permissions[19].op`: Операция права доступа не существует.
- `REQ_UNCOVERED` `analysis.user_stories`: Требование REQ-01 не связано с историей, правилом, NFR или исключением из объёма.
- `REQ_UNCOVERED` `analysis.user_stories`: Требование REQ-14 не связано с историей, правилом, NFR или исключением из объёма.
- `REQ_UNCOVERED` `analysis.user_stories`: Требование REQ-19 не связано с историей, правилом, NFR или исключением из объёма.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-07]`: У порога правила BR-05 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
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
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-04]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-08]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-11]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-15]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `SM_DEADLOCK` `state_machines.ParkingSession.states[3]`: Нетерминальное состояние не имеет выхода.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду start_session.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду end_session.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду cancel_session.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду update_vehicle_location.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду create_parking_zone.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду update_parking_zone.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду delete_parking_zone.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду configure_payment_adapter.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду monitor_events.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду generate_payment_link.
- `US_NO_ENDPOINT` `analysis.user_stories[US-01]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-02]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-03]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-04]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-05]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-06]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-07]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-08]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-09]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-10]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-11]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-12]`: История не связана с доступной своей роли операцией API.

Честных флагов сомнения/зависимости: 195.

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

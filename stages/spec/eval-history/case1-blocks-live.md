# Оценка analysis/spec

Режим: `live`. Дата UTC: 2026-10-30T13:19:30.625579+00:00.

Записанные ответы не являются прогоном настоящей модели; неизвестные метрики обозначены `—`.

| Кейс | Статус | REQ | Цитаты | ISS / Q | BR с AC | G1 до → после | Вызовы | Токены |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| case1 | partial | 35 | 0.8285714285714286 | 34 / 8 | 1.0 | 165 → 165 | 108 | 300779 |

## case1

Статус: `partial`. Время: 1215143 мс.

Артефакты и сырые выходы модели: `/home/haus/Projects/rwb-ai-hack/workspaces/eval/20261030T125915476642/case1`.

Находки после ремонта:

- `REF_UNRESOLVED` `analysis.assumptions[ASM-03]`: Ссылка «REQ-07, REQ-08» не разрешается.
- `REF_UNRESOLVED` `entities.ParkingZone.owner`: Ссылка «ParkingZoneService» не разрешается.
- `REF_UNRESOLVED` `entities.ParkingSession.owner`: Ссылка «ParkingSessionService» не разрешается.
- `REF_UNRESOLVED` `entities.ParkingSession.fields.payment_status`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `entities.Vehicle.owner`: Ссылка «VehicleTrackingService» не разрешается.
- `REF_UNRESOLVED` `entities.ParkingEvent.owner`: Ссылка «EventService» не разрешается.
- `REF_UNRESOLVED` `entities.ParkingEvent.fields.event_type`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `entities.PaymentService.owner`: Ссылка «PaymentAdapter» не разрешается.
- `REF_UNRESOLVED` `state_machines.ParkingSessionStateMachine.transitions[3].trigger.timer`: Ссылка «warning_lead_time» не разрешается.
- `REF_UNRESOLVED` `state_machines.ParkingSessionStateMachine.transitions[4].trigger.timer`: Ссылка «session_end_time» не разрешается.
- `REF_UNRESOLVED` `state_machines.ParkingSessionStateMachine.transitions[5].trigger.timer`: Ссылка «session_end_time» не разрешается.
- `REF_UNRESOLVED` `hooks.gps_accuracy_validator.rule`: Ссылка «Проверить, что точность GPS не превышает gps_accuracy_meters метров» не разрешается.
- `REF_UNRESOLVED` `hooks.gps_accuracy_validator.in`: Ссылка «gps_accuracy_meters» не разрешается.
- `REF_UNRESOLVED` `hooks.geofence_entry_detector.rule`: Ссылка «Определить пересечение границы зоны внутрь (въезд)» не разрешается.
- `REF_UNRESOLVED` `hooks.zone_polygon_renderer.rule`: Ссылка «Сформировать данные для отображения полигона зоны и текстовой метки номера зоны» не разрешается.
- `REF_UNRESOLVED` `hooks.zone_polygon_renderer.out`: Ссылка «polygon_render_data» не разрешается.
- `REF_UNRESOLVED` `hooks.parking_params_display.rule`: Ссылка «Собрать параметры парковки для отображения пользователю» не разрешается.
- `REF_UNRESOLVED` `hooks.parking_params_display.out`: Ссылка «parking_info_view» не разрешается.
- `REF_UNRESOLVED` `hooks.session_record_validator.rule`: Ссылка «Проверить наличие всех обязательных полей активной сессии» не разрешается.
- `REF_UNRESOLVED` `hooks.location_update_interval_validator.rule`: Ссылка «Проверить, что интервал обновления геолокации соответствует location_update_interval и задержка не превышает location_max_delay» не разрешается.
- `REF_UNRESOLVED` `hooks.location_update_interval_validator.in`: Ссылка «location_update_interval» не разрешается.
- `REF_UNRESOLVED` `hooks.location_update_interval_validator.in`: Ссылка «location_max_delay» не разрешается.
- `REF_UNRESOLVED` `hooks.geofence_exit_detector.rule`: Ссылка «Определить пересечение границы зоны наружу (выход)» не разрешается.
- `REF_UNRESOLVED` `hooks.zone_transition_detector.rule`: Ссылка «Определить пересечение границы новой зоны (переход)» не разрешается.
- `REF_UNRESOLVED` `hooks.event_priority_resolver.rule`: Ссылка «При одновременном срабатывании выхода и перехода приоритет отдаётся событию перехода» не разрешается.
- `REF_UNRESOLVED` `hooks.event_priority_resolver.in`: Ссылка «geofence_exit_detector» не разрешается.
- `REF_UNRESOLVED` `hooks.event_priority_resolver.in`: Ссылка «zone_transition_detector» не разрешается.
- `REF_UNRESOLVED` `hooks.event_priority_resolver.out`: Ссылка «event_type» не разрешается.
- `REF_UNRESOLVED` `hooks.session_end_tolerance_validator.rule`: Ссылка «Проверить, что отклонение фактического времени окончания от заданного не превышает session_end_tolerance» не разрешается.
- `REF_UNRESOLVED` `hooks.session_end_tolerance_validator.in`: Ссылка «session_end_tolerance» не разрешается.
- `REF_UNRESOLVED` `hooks.payment_warning_trigger.rule`: Ссылка «Сформировать предупреждение о необходимости проверки или новой оплаты при изменении стоимости» не разрешается.
- `REF_UNRESOLVED` `hooks.payment_warning_trigger.out`: Ссылка «warning_notification» не разрешается.
- `REF_UNRESOLVED` `hooks.payment_deep_link_generator.rule`: Ссылка «Сформировать Deep Link для перехода к официальному сервису оплаты» не разрешается.
- `REF_UNRESOLVED` `hooks.payment_deep_link_generator.out`: Ссылка «deep_link_url» не разрешается.
- `REF_UNRESOLVED` `hooks.history_retention_filter.rule`: Ссылка «Определить, отображается ли сессия в истории в зависимости от history_retention_days» не разрешается.
- `REF_UNRESOLVED` `hooks.history_retention_filter.in`: Ссылка «history_retention_days» не разрешается.
- `REF_UNRESOLVED` `hooks.kotlin_version_validator.rule`: Ссылка «Проверить, что версия Kotlin и платформа соответствуют требованиям» не разрешается.
- `REF_UNRESOLVED` `hooks.kotlin_version_validator.in`: Ссылка «kotlin_version» не разрешается.
- `REF_UNRESOLVED` `hooks.kotlin_version_validator.in`: Ссылка «mobile_platform» не разрешается.
- `REF_UNRESOLVED` `hooks.database_version_validator.rule`: Ссылка «Проверить версии PostgreSQL и PostGIS» не разрешается.
- `REF_UNRESOLVED` `hooks.database_version_validator.in`: Ссылка «postgres_version» не разрешается.
- `REF_UNRESOLVED` `hooks.database_version_validator.in`: Ссылка «postgis_version» не разрешается.
- `REF_UNRESOLVED` `hooks.docker_container_validator.rule`: Ссылка «Проверить наличие контейнеров для backend, БД, mock-сервиса оплаты и админ-интерфейса» не разрешается.
- `REF_UNRESOLVED` `hooks.docker_container_validator.in`: Ссылка «docker_compose_config» не разрешается.
- `REF_UNRESOLVED` `hooks.cicd_pipeline_validator.rule`: Ссылка «Проверить наличие этапов сборки, тестирования и деплоя в CI/CD пайплайне» не разрешается.
- `REF_UNRESOLVED` `hooks.cicd_pipeline_validator.in`: Ссылка «cicd_pipeline_config» не разрешается.
- `REF_UNRESOLVED` `hooks.admin_interface_validator.rule`: Ссылка «Проверить наличие разделов мониторинга событий, истории сессий и конфигурации в админ-интерфейсе» не разрешается.
- `REF_UNRESOLVED` `hooks.admin_interface_validator.in`: Ссылка «admin_menu_config» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_event_structure.rule`: Ссылка «Событие должно содержать непустые поля: event_type, timestamp, session_id, event_data.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_test_data_counts.rule`: Ссылка «Количество записей ParkingSession должно быть равно test_sessions_count, а количество записей ParkingZone — test_zones_count.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_test_coverage.rule`: Ссылка «Покрытие кода тестами должно быть не менее test_coverage_percent процентов.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_test_coverage.in`: Ссылка «test_coverage_report» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_api_documentation_coverage.rule`: Ссылка «Доля задокументированных эндпоинтов в OpenAPI должна быть не менее api_coverage_percent процентов.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_api_documentation_coverage.in`: Ссылка «openapi_spec» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_documentation_set.rule`: Ссылка «Набор документов должен включать: системное описание, руководство пользователя, API-документация.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_documentation_set.in`: Ссылка «documentation_files» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_payment_interface.rule`: Ссылка «Объект PaymentService должен реализовывать интерфейс payment_interface.» не разрешается.
- `REF_UNRESOLVED` `hooks.decide_fallback_payment.rule`: Ссылка «Если внешний сервис оплаты недоступен, использовать mock-сервис.» не разрешается.
- `REF_UNRESOLVED` `hooks.decide_fallback_payment.out`: Ссылка «use_mock_payment» не разрешается.
- `REF_UNRESOLVED` `hooks.handle_session_start_error.rule`: Ссылка «При ошибке запуска сессии отобразить сообщение об ошибке и предложить повторить действие.» не разрешается.
- `REF_UNRESOLVED` `hooks.handle_session_start_error.in`: Ссылка «error_message» не разрешается.
- `REF_UNRESOLVED` `hooks.detect_zone_entry.rule`: Ссылка «Определить въезд в зону при пересечении границы зоны внутрь.» не разрешается.
- `REF_UNRESOLVED` `hooks.detect_zone_entry.out`: Ссылка «is_zone_entry» не разрешается.
- `REF_UNRESOLVED` `hooks.format_entry_notification.rule`: Ссылка «Сформировать уведомление, содержащее номер зоны и стоимость парковки.» не разрешается.
- `REF_UNRESOLVED` `hooks.format_entry_notification.out`: Ссылка «notification_message» не разрешается.
- `REF_UNRESOLVED` `hooks.format_session_end_time.rule`: Ссылка «Отобразить время окончания сессии в формате time_format.» не разрешается.
- `REF_UNRESOLVED` `hooks.format_session_end_time.out`: Ссылка «formatted_end_time» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_warning_timing.rule`: Ссылка «Время отправки предупреждения должно быть за warning_lead_time до окончания сессии с отклонением не более warning_tolerance.» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_warning_timing.in`: Ссылка «warning_sent_time» не разрешается.
- `REF_UNRESOLVED` `hooks.validate_warning_timing.in`: Ссылка «session_end_time» не разрешается.
- `REF_UNRESOLVED` `hooks.handle_zone_exit_error.rule`: Ссылка «При ошибке покидания зоны зафиксировать событие в логе и уведомить администратора.» не разрешается.
- `REF_UNRESOLVED` `hooks.handle_zone_exit_error.in`: Ссылка «error_message» не разрешается.
- `REF_UNRESOLVED` `hooks.decide_payment_check_prompt.rule`: Ссылка «Отобразить предложение проверить оплату при переходе в зону с другой стоимостью.» не разрешается.
- `REF_UNRESOLVED` `hooks.decide_payment_check_prompt.in`: Ссылка «current_zone» не разрешается.
- `REF_UNRESOLVED` `hooks.decide_payment_check_prompt.out`: Ссылка «show_payment_check» не разрешается.
- `REF_UNRESOLVED` `hooks.filter_events_by_criteria.rule`: Ссылка «Отфильтровать события по дате и типу для отображения в таблице.» не разрешается.
- `REF_UNRESOLVED` `hooks.filter_events_by_criteria.in`: Ссылка «date_filter» не разрешается.
- `REF_UNRESOLVED` `hooks.filter_events_by_criteria.in`: Ссылка «type_filter» не разрешается.
- `REF_UNRESOLVED` `hooks.filter_events_by_criteria.out`: Ссылка «filtered_events» не разрешается.
- `REF_UNRESOLVED` `hooks.retrieve_event_history.rule`: Ссылка «Вернуть список сохраненных событий из базы данных через API.» не разрешается.
- `REF_UNRESOLVED` `hooks.retrieve_event_history.out`: Ссылка «event_history» не разрешается.
- `REF_UNRESOLVED` `commands.update_vehicle_location.input.vehicle_id`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `commands.start_parking_session.effects`: Ссылка «start_session» не разрешается.
- `REF_UNRESOLVED` `commands.cancel_parking_session.input.session_id`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `commands.cancel_parking_session.effects`: Ссылка «session_cancelled» не разрешается.
- `REF_UNRESOLVED` `commands.log_zone_exit_error.input.event_type`: Ссылка «None» не разрешается.
- `REF_UNRESOLVED` `commands.query_parking_events.input.type_filter`: Ссылка «None» не разрешается.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-06]`: У порога правила BR-06 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-14]`: У порога правила BR-14 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-15]`: У порога правила BR-15 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-20]`: У порога правила BR-20 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
- `BR_NO_BOUNDARY` `analysis.acceptance[AC-31]`: У порога правила BR-32 нет примеров N−1, N и N+1 в одной колонке таблицы сценария.
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
- `BR_NO_HOOK` `hooks`: Правило BR-26 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-27 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-28 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-29 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-30 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-31 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-32 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-33 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-34 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-35 не представлено хуком или декларативным правилом.
- `BR_NO_HOOK` `hooks`: Правило BR-36 не представлено хуком или декларативным правилом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-02]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-07]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-08]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-09]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-12]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-14]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-16]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-24]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-25]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-26]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `AC_NOT_TESTABLE` `analysis.acceptance[AC-27]`: Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду update_vehicle_location.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду start_parking_session.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду cancel_parking_session.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду update_parking_zone.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду update_payment_service.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду start_session.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду cancel_session.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду log_zone_exit_error.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду query_parking_events.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду query_parking_events.
- `RBAC_ORPHAN` `permissions`: Роль driver не имеет права выполнять команду query_parking_sessions.
- `RBAC_ORPHAN` `permissions`: Роль admin не имеет права выполнять команду query_parking_sessions.
- `US_NO_ENDPOINT` `analysis.user_stories[US-06]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-10]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-16]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-19]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-20]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-21]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-22]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-23]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-24]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-25]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-26]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-28]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-29]`: История не связана с доступной своей роли операцией API.
- `US_NO_ENDPOINT` `analysis.user_stories[US-30]`: История не связана с доступной своей роли операцией API.

Честных флагов сомнения/зависимости: 1100.

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

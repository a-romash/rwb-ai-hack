# Каталог паттернов и виджетов `ui.json`

Владелец — Артём. Потребители: генератор экранов (Иван), E2E по проходам (Тимофей), отчёт.
Схема — `contracts/ui.py` (`UiSpec`, `load_ui`), пример — `contracts/fixtures/tickets/ui.json`.
Машинные таблицы этого каталога лежат там же: `PATTERN_SOURCES`, `PATTERN_WIDGETS`, `WIDGET_REFS`,
`REQUIRED_STATES`. Если таблица здесь и в коде расходятся — прав код, а этот файл надо поправить.

Схема проверяет только сам файл: словари, форму, допустимость виджета для паттерна, префиксы `testid`.
Ссылки на `app.json` (сущности, поля, queries, commands, events, роли, AC) проверяет гейт G1.5.
Генератор может считать, что после G1.5 все ссылки разрешаются.

## 1. Экран

```json
"TicketList": {
  "platform": "web", "roles": ["engineer"], "pattern": "list", "title": "Заявки",
  "source": {"query": "OpenTickets"},
  "widgets": [...], "filters": [...], "actions": [...],
  "live": ["TicketTaken"], "states": {"loading": "…", "empty": "…", "error": "…", "forbidden": "…"},
  "nav": ["TicketDetail"]
}
```

| Поле | Обязательно | Смысл |
|---|---|---|
| ключ | да | имя экрана в PascalCase; из него маршрут и префикс `testid` (`TicketList` → `ticket-list`) |
| `platform` | да | `web` → `admin-web/`, `mobile` → `mobile-web/` (PWA) |
| `roles` | да | кто видит экран; генератор ставит guard маршрута, остальным — состояние `forbidden` |
| `pattern` | да | один из 11 паттернов ниже |
| `title` | да | заголовок экрана и пункта меню |
| `source` | по паттерну | ровно одно из `query`, `entity`, `command`, `params` (см. §3) |
| `widgets` | нет | содержимое экрана по порядку; допустимые виды зависят от паттерна |
| `filters` | нет | фильтры списка по полям: `{field, testid}`; контрол по типу поля |
| `actions` | нет | команды экрана: в строке списка или в панели действий (см. §5) |
| `live` | нет | события `app.json`, по которым экран перечитывает данные (SSE продукта) |
| `states` | для экранов с данными | тексты состояний; ключи из `loading`, `empty`, `error`, `forbidden`, `offline` |
| `nav` | нет | экраны, на которые можно перейти отсюда (ссылка из строки, кнопка, вкладка) |

**Экран с данными** (`Screen.has_data`): есть `source` или виджет `kpi`, `map_layer`, `timeline`.
У него обязательны все состояния `REQUIRED_STATES`: `loading`, `empty`, `error`, `forbidden`,
а для `mobile` ещё `offline`. `offline` у `web` запрещён схемой.

## 2. Паттерны

| Паттерн | Для чего | `source` | Виджеты | Веб (`admin-web`, Angular Material) | PWA (`mobile-web`) |
|---|---|---|---|---|---|
| `list` | Таблица с фильтрами, поиском, страницами | `query` \| `entity` | `field`, `status`, `countdown`, `file` | `mat-table` + `mat-paginator` + `mat-sort`; фильтры над таблицей | `mat-list` карточками, фильтры в `MatBottomSheet` |
| `detail` | Карточка записи: поля, статус, история, действия | `entity` | `field`, `status`, `countdown`, `timeline`, `map_layer`, `action_button`, `file` | `mat-card`; группы полей — секции или `mat-tab-group` | `mat-card` на всю ширину, действия прижаты к низу |
| `form` | Создание и изменение записи или ввод команды | `entity` \| `command` | `field`, `file`, `scan` | `mat-form-field` + Reactive Forms, ошибки у полей | поля в одну колонку, крупные контролы |
| `wizard` | Длинная команда по шагам | `command` | `field`, `file`, `scan` | `mat-stepper` (шаг = `group`) | `mat-stepper` вертикальный |
| `dashboard` | Счётчики и графики | — | `kpi`, `map_layer`, `timeline` | `mat-grid-list` из `mat-card` | `mat-card` стопкой |
| `map` | Объекты и области на карте | `query` \| `entity` | `map_layer`, `field`, `status`, `action_button` | MapLibre GL (`@maplibre/ngx-maplibre-gl`), всплывающая карточка объекта | MapLibre на весь экран, своя точка из Geolocation API |
| `feed` | Лента событий в реальном времени | `query` \| `entity` \| нет | `field`, `status`, `countdown`, `timeline` | `mat-list` + поток SSE, новые сверху | `mat-list` + поток SSE |
| `action` | Один крупный сценарий: «начать», «завершить», таймер | `command` \| `entity` | `field`, `status`, `countdown`, `action_button`, `scan`, `map_layer`, `file` | `mat-card` + `mat-raised-button` | крупная кнопка внизу, таймер по центру |
| `settings` | Параметры пользователя и `params` для админа | `params` | `field` | `mat-slide-toggle`, формы | `mat-list` + переключатели |
| `calendar` | Брони, смены, сроки по дням | `query` \| `entity` | `field`, `status`, `countdown` | сетка на `mat-grid-list` | список дней |
| `kanban` | Записи по состояниям машины | `query` \| `entity` | `field`, `status`, `countdown` | колонки по `states` машины + `cdkDrag` (перетаскивание = команда перехода) | `mat-tab-group`, вкладка на состояние |

Уточнения:
- `list` с `entity` — все записи сущности в пределах прав роли (`scope` из `permissions`); с `query` — результат query.
- `form` с `entity` — создание (`Entity.create`) и изменение (`Entity.update`) по маршруту `new` / `:id/edit`;
  с `command` — ввод полей `input` команды, запись берётся из маршрута.
- `kanban` — колонки и их порядок берутся из машины состояний поля `status` сущности; перетаскивание
  разрешено, только если между колонками есть переход с триггером `command`, доступный роли.
- `settings` с `params` — значения `params` из `app.json`, только для чтения или для роли с правом на изменение.

## 3. Источник `source`

| Ключ | Значение | Откуда данные |
|---|---|---|
| `query` | имя из `app.json.queries` | GET по query; фильтр и сортировка — из query |
| `entity` | имя из `app.json.entities` | CRUD-эндпоинты сущности; `detail` — по `:id` из маршрута |
| `command` | имя из `app.json.commands` | форма `input` команды, отправка — POST команды |
| `params` | список ключей `app.json.params` | чтение и изменение параметров |

## 4. Виджеты

Общие поля: `kind`, `testid` (обязательны), `label` — ключ `copy` вместо подписи поля из `app.json`,
`group` — ключ `copy` группы (секция карточки, набор полей формы, шаг мастера).

| Виджет | Обязательная ссылка | Что показывает | Веб | PWA |
|---|---|---|---|---|
| `field` | `field` | поле сущности или ввода команды; контрол по типу (таблица ниже) | см. ниже | см. ниже |
| `status` | `field` (тип `state`) | состояние машины; цвет по группе | `mat-chip` | `mat-chip` |
| `countdown` | `field` (`datetime`) | сколько осталось до срока; после срока — «просрочено» | текст + `mat-icon` | текст крупно |
| `kpi` | `query`; `agg` (`count` по умолчанию, `sum`, `avg`, `min`, `max`), `field` для всех кроме `count` | одно число по query | `mat-card` с числом | `mat-card` с числом |
| `timeline` | `field` (тип `state`) | журнал переходов записи из таблицы событий | `mat-list` с датами | `mat-list` |
| `map_layer` | `query` с полем `geo_*` | точки, линии, полигоны | слой MapLibre | слой MapLibre |
| `action_button` | `command` | кнопка команды внутри содержимого (карточка, экран `action`) | `mat-raised-button` | крупная кнопка |
| `scan` | `field` (строка) | камера → строка (QR, штрихкод) в поле | `BarcodeDetector` или `@zxing/browser` | то же, задняя камера |
| `file` | `field` (тип `file`) | загрузка и просмотр файла | `<input type="file">` | `<input type="file" capture>` |

`field` — путь `Entity.field` или `Command.input` (поле ввода команды, только в `form`/`wizard` с `source.command`).

Контрол `field` по типу поля `app.json`:

| Тип | Просмотр | Ввод |
|---|---|---|
| `string`, `text` | текст | `matInput`, для `text` — `textarea` |
| `int`, `decimal` | число по локали `meta.lang` | `matInput type=number` |
| `money` | сумма с валютой | `matInput` + суффикс валюты |
| `bool` | «да» / «нет» | `mat-slide-toggle` (форма), `mat-checkbox` (фильтр) |
| `date`, `datetime` | дата в `meta.timezone` | `mat-datepicker` (+ время для `datetime`) |
| `duration`, `interval` | «4 ч», «с 9:00 до 18:00» | два поля или маска |
| `enum` | подпись из `types.<T>.labels` | `mat-select` |
| `ref` | подпись записи-ссылки, ссылка на её `detail`, если есть | `mat-autocomplete` |
| `state` | как `status` | не вводится, меняется командами |
| `geo_point`, `geo_line`, `geo_polygon` | мини-карта | выбор на карте; в PWA — кнопка «Моё место» (Geolocation API) |
| `file` | как виджет `file` | как виджет `file` |
| `json` | свёрнутый JSON | `textarea` с проверкой |

Цвет `status` по группе состояния: `active` — синий, `warning` — жёлтый, `done` — зелёный, `error` — красный.
Группу выводит генератор: `initial` → `active`, `final` → `done`, состояние, куда ведёт переход с триггером
`timer`, → `warning`; остальные — `active`.

## 5. Действия: `actions` и `action_button`

```json
{"command": "TakeTicket", "testid": "ticket-list.take", "confirm": true,
 "copy": "ticket.take.confirm", "then": "TicketDetail"}
```

- `command` — имя команды из `app.json.commands` или операция `Entity.create|update|delete`.
- Кнопка **скрыта**, если у роли нет права на операцию (`permissions`), и **неактивна**, если из текущего состояния
  записи нет перехода по этой команде. Защита на бэкенде остаётся — кнопка только подсказка.
- `confirm: true` — диалог подтверждения (`MatDialog`; в PWA — `MatBottomSheet`) с текстом `copy[<copy>]`.
- `then` — экран, который открывается после успеха (для `detail` — с `:id` той же записи). Без `then` экран
  остаётся и перечитывает данные.
- Если у команды есть обязательные поля `input`, кнопка не отправляет её сразу, а открывает экран `form`
  с `source.command` этой команды (он должен быть в `nav`).
- `actions` в `list`, `kanban`, `map` — действия **строки** (кнопка в строке, иконка в карточке);
  в остальных паттернах — панель действий экрана (веб — справа в заголовке, PWA — снизу).
- `action_button` — та же кнопка, но поставленная в поток виджетов (карточка, экран `action`).
- Ошибка хука `validator`/`policy` показывается текстом `copy["error.<Hook>"]`: у поля, если ошибка
  относится к полю, иначе — `MatSnackBar`.

## 6. Живые обновления `live`

Список событий `app.json` (включая выводимые генератором `<Entity><Transition>ed`, например `TicketTaken`).
Экран подписывается на SSE продукта и при событии своей сущности перечитывает `source` (список — целиком,
`detail` — только если `id` совпал). Ленты `feed` добавляют запись сверху без перечитывания.

## 7. Меню, главный экран, навигация

- `menus.<role>.<platform>` — пункты меню роли по порядку (веб — `mat-sidenav`, PWA — нижняя навигация, до 5 пунктов).
- `home.<role>.<platform>` — экран после входа.
- Экран достижим, если до него есть путь от `home` по `menus` и `nav`. Недостижимые экраны прохода — ошибка G1.5.
- Переход из строки списка в `nav`-экран `detail` — клик по строке; на прочие `nav`-экраны — кнопка или ссылка.

## 8. `testid`

- Вид `<screen-kebab>.<element>`: `ticket-list.take`, `ticket-detail.status`. Элемент — kebab-case.
- Уникален в пределах приложения (G1.5 `TESTID_DUP`), префикс совпадает с экраном (схема).
- Генератор ставит `data-testid`:
  - `field` / `status` / `countdown` в `list` — на ячейку каждой строки; строка — `<screen>.row` с атрибутом
    `data-row-id`;
  - `actions` в `list` — на кнопку в каждой строке;
  - фильтр — на контрол фильтра;
  - всё остальное — на один элемент.
- Состояния экрана — служебные `testid`: `<screen>.state-loading`, `.state-empty`, `.state-error`,
  `.state-forbidden`, `.state-offline`. В `ui.json` их не пишут, они резервированы.
- Page objects `*/e2e/pages/*` генерируются из этих `testid`.

## 9. Проходы `walks`

Один проход на US: роль, платформа, шаги, покрываемые AC. Из прохода механически получаются E2E-тест
(заголовок начинается с `@AC-xx` для каждого из `covers`) и раздел пользовательской документации.

| Шаг | Форма | Что делает E2E |
|---|---|---|
| `open` | `{"open": "TicketList"}` | вход ролью, переход на экран |
| `fill` | `{"fill": "Ticket.title", "value": <значение>}` | ввод в виджет поля на текущем экране |
| `tap` | `{"tap": "TakeTicket", "row": {"seed": "Ticket[0]"}}` | нажатие действия; если `tap` — имя экрана из `nav`, переход на него. `row` — в какой строке списка |
| `scan` | `{"scan": "Equipment.inventory_no", "value": <значение>}` | подстановка значения вместо камеры |
| `expect` | `{"expect": {...}}` | проверки (все указанные должны выполниться) |

Поля `expect`: `screen` — открыт экран; `status` — виджет `status` показывает состояние; `error` — команду
отклонил хук с этим именем; `copy` — виден текст по ключу; `visible` — видны элементы с этими `testid`;
`row` — в списке есть строка записи сида. Если сразу после `tap` идёт `expect` с `error`, команда считается
отклонённой: экран не меняется, `then` не срабатывает.

Проход начинается с `open`. Экран после каждого шага однозначен: `open` и `tap` по экрану из `nav` открывают его,
`tap` по действию с `then` открывает `then`, остальные шаги экран не меняют. G1.5 проверяет проход по этим правилам.

**Значения** — только ссылки, литералы дают предупреждение G1.5 `WALK_LITERAL`:
- `{"seed": "Ticket[0].title"}` — значение из `app.json.seed`; `{"seed": "Ticket[0]"}` — сама запись (для `row`);
- `{"param": "SLA_HIGH"}` — значение из `app.json.params`;
- `{"gen": "valid"}` — любое корректное значение по типу поля, его создаёт тестовый набор (для полей ввода
  команд, которых нет в сиде).

Записи сида адресуются по индексу в `seed.<Entity>`; E2E находит строку по её первому строковому полю.

## 10. Тексты `copy`, устройства `device`

- `copy` — все тексты, кроме заголовков экранов, подписей полей (`app.json`) и состояний (`states`).
  Ключи в нижнем регистре через точку; тексты ошибок хуков — `error.<HookName>`.
  Все ключи, на которые ссылаются `label`, `group`, `actions[].copy`, `expect.copy`, должны быть заданы (G1.5).
- Язык текстов — `app.json.meta.lang`.
- `device.<platform>` — возможности устройства из закрытого списка. В PWA через браузерные API:

| Возможность | API | Ограничение |
|---|---|---|
| `location` | Geolocation API | только пока приложение открыто, фонового трекинга нет |
| `local_notification` | Notification API через service worker | нужно разрешение пользователя |
| `external_link` | переход по ссылке | — |
| `scan_code` | `BarcodeDetector` или `@zxing/browser` | нужна камера |
| `file_pick` | `<input type="file" capture>` | — |

В E2E — мобильная эмуляция Playwright, `geolocation` и `permissions` контекста.

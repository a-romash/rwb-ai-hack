# Администратор

## US-11 — чтобы события парковки (въезд, выезд, смена зоны, предупреждения) отображались в административном интерфейсе и сохранялись в истории
1. `{"open": "ParkingEventList"}`
2. `{"expect": {"screen": "ParkingEventList", "visible": ["parking-event-list.session-id", "parking-event-list.type", "parking-event-list.occurred-at", "parking-event-list.zone-id", "parking-event-list.message"]}}`
3. `{"tap": "ParkingEventDetail"}`
4. `{"expect": {"screen": "ParkingEventDetail", "visible": ["parking-event-detail.session-id", "parking-event-detail.type", "parking-event-detail.occurred-at", "parking-event-detail.zone-id", "parking-event-detail.message"]}}`
5. `{"open": "ParkingEventList"}`
6. `{"tap": "ParkingEventDetail"}`
7. `{"expect": {"screen": "ParkingEventDetail", "visible": ["parking-event-detail.session-id", "parking-event-detail.type", "parking-event-detail.occurred-at", "parking-event-detail.zone-id", "parking-event-detail.message"]}}`
8. `{"open": "ParkingEventList"}`
9. `{"tap": "ParkingEventDetail"}`
10. `{"expect": {"screen": "ParkingEventDetail", "visible": ["parking-event-detail.session-id", "parking-event-detail.type", "parking-event-detail.occurred-at", "parking-event-detail.zone-id", "parking-event-detail.message"]}}`
11. `{"open": "AdminDashboard"}`
12. `{"expect": {"screen": "AdminDashboard", "visible": ["admin-dashboard.total-vehicles", "admin-dashboard.total-zones", "admin-dashboard.total-events"]}}`

## US-12 — чтобы я мог просматривать тарифы парковочных зон через доступную мне операцию API
1. `{"open": "GetZoneTariffForm"}`
2. `{"fill": "GetZoneTariff.zoneId", "value": {"seed": "ParkingZone[0].externalZoneId"}}`
3. `{"tap": "GetZoneTariff"}`
4. `{"expect": {"screen": "ParkingZoneDetail", "visible": ["parking-zone-detail.tariff", "parking-zone-detail.price", "parking-zone-detail.price-description", "parking-zone-detail.state"]}}`

## US-13 — чтобы в системе была реализована модель событий, позволяющая фиксировать и просматривать все значимые события парковки
1. `{"open": "AdminDashboard"}`
2. `{"expect": {"screen": "AdminDashboard", "visible": ["admin-dashboard.total-vehicles", "admin-dashboard.total-zones", "admin-dashboard.total-events"]}}`

## US-14 — чтобы для системы были сформированы тестовые данные, включая геоданные парковочных зон и демонстрационные маршруты
1. `{"open": "AdminDashboard"}`
2. `{"expect": {"screen": "AdminDashboard", "visible": ["admin-dashboard.total-vehicles", "admin-dashboard.total-zones", "admin-dashboard.total-events"]}}`

## US-15 — чтобы для системы были разработаны автоматизированные тесты, покрывающие основные функциональные требования
1. `{"open": "AdminDashboard"}`
2. `{"expect": {"screen": "AdminDashboard", "visible": ["admin-dashboard.total-vehicles", "admin-dashboard.total-zones", "admin-dashboard.total-events"]}}`

## US-16 — чтобы для системы была подготовлена системная, продуктовая и пользовательская документация
1. `{"open": "AdminDashboard"}`
2. `{"expect": {"screen": "AdminDashboard", "visible": ["admin-dashboard.total-vehicles", "admin-dashboard.total-zones", "admin-dashboard.total-events"]}}`

## US-17 — чтобы интеграция с внешними сервисами (например, оплатой парковки) была реализована через адаптер и mock-сервис
1. `{"open": "AdminDashboard"}`
2. `{"expect": {"screen": "AdminDashboard", "status": "active", "visible": ["admin-dashboard.total-vehicles", "admin-dashboard.total-zones", "admin-dashboard.total-events"]}}`

## US-18 — чтобы в проверочном сценарии служебный автомобиль мог двигаться по заданному маршруту с использованием GPS-координат, демонстрационного mock-маршрута или данных официального сервиса парковок Санкт-Петербурга
1. `{"open": "AdminDashboard"}`
2. `{"open": "VehicleList"}`
3. `{"tap": "VehicleDetail"}`
4. `{"expect": {"screen": "VehicleDetail", "visible": ["vehicle-detail.route-id", "vehicle-detail.current-location", "vehicle-detail.status", "vehicle-detail.last-position-at"]}}`

## US-19 — чтобы просматривать тарифы парковочных зон и историю парковочных событий в административном интерфейсе
1. `{"expect": {"screen": "AdminDashboard", "visible": ["admin-dashboard.total-vehicles", "admin-dashboard.total-zones", "admin-dashboard.total-events"]}}`
2. `{"open": "ParkingZoneList"}`
3. `{"tap": "ParkingZoneDetail"}`
4. `{"expect": {"screen": "ParkingZoneDetail", "visible": ["parking-zone-detail.external-zone-id", "parking-zone-detail.display-name", "parking-zone-detail.state", "parking-zone-detail.price"], "row": {"seed": "ParkingZone[0]"}}}`
5. `{"fill": "GetZoneTariff.zoneId", "value": {"seed": "ParkingZone[0].externalZoneId"}}`
6. `{"tap": "GetZoneTariff"}`
7. `{"expect": {"screen": "ParkingZoneDetail", "status": "active", "visible": ["parking-zone-detail.tariff", "parking-zone-detail.price", "parking-zone-detail.min-time", "parking-zone-detail.time-step"]}}`
8. `{"open": "ParkingEventList"}`
9. `{"tap": "ParkingEventDetail"}`
10. `{"expect": {"screen": "ParkingEventDetail", "visible": ["parking-event-detail.session-id", "parking-event-detail.type", "parking-event-detail.occurred-at", "parking-event-detail.zone-id"], "row": {"seed": "ParkingEvent[0]"}}}`
11. `{"fill": "GetParkingEvents.vehicleId", "value": {"seed": "ParkingSession[0].vehicleId"}}`
12. `{"tap": "GetParkingEvents"}`
13. `{"expect": {"screen": "ParkingEventDetail", "status": "in_zone", "visible": ["parking-event-detail.session-id", "parking-event-detail.type"]}}`

## US-20 — чтобы система не требовала разработки собственного платежного механизма, а использовала внешний сервис оплаты
1. `{"open": "AdminDashboard"}`
2. `{"expect": {"screen": "AdminDashboard"}}`

Скриншоты текущего прогона не предоставлены.

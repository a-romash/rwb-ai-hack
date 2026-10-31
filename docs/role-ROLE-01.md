# Водитель

## US-01 — чтобы система была настроена на выполнение работ техническими службами на нескольких объектах Санкт-Петербурга на служебных автомобилях
1. `{"open": "MobileParkingZoneList"}`
2. `{"expect": {"screen": "MobileParkingZoneList", "status": "active", "row": {"seed": "ParkingZone[0]"}}}`
3. `{"tap": "MobileParkingZoneDetail"}`
4. `{"expect": {"screen": "MobileParkingZoneDetail", "status": "active", "visible": ["mobile-parking-zone-detail.external-zone-id", "mobile-parking-zone-detail.display-name", "mobile-parking-zone-detail.state"]}}`

## US-02 — чтобы мобильное приложение определяло местоположение моего служебного автомобиля по GPS
1. `{"open": "MobileVehicleList"}`
2. `{"tap": "MobileVehicleDetail"}`
3. `{"tap": "ReportVehicleLocation"}`
4. `{"fill": "ReportVehicleLocation.vehicleId", "value": {"seed": "Vehicle[0].licensePlate"}}`
5. `{"fill": "ReportVehicleLocation.latitude", "value": {"seed": "Vehicle[0].currentLocation"}}`
6. `{"fill": "ReportVehicleLocation.longitude", "value": {"seed": "Vehicle[0].currentLocation"}}`
7. `{"fill": "ReportVehicleLocation.timestamp", "value": {"gen": "valid"}}`
8. `{"tap": "ReportVehicleLocation"}`
9. `{"expect": {"screen": "MobileVehicleDetail", "visible": ["mobile-vehicle-detail.current-location", "mobile-vehicle-detail.last-position-at"]}}`

## US-03 — чтобы система отслеживала перемещение автомобиля, определяла въезд в зону платной парковки, выход из текущей зоны или переход в другую зону, и уведомляла меня об изменении статуса парковки
1. `{"open": "MobileParkingZoneList"}`
2. `{"tap": "MobileParkingZoneDetail"}`
3. `{"tap": "MobileGetCurrentZoneForm"}`
4. `{"fill": "GetCurrentZone.vehicleId", "value": {"seed": "ParkingSession[0].vehicleId"}}`
5. `{"tap": "GetCurrentZone"}`
6. `{"expect": {"screen": "MobileParkingZoneDetail", "status": "in_zone"}}`

## US-04 — чтобы в мобильном приложении отображался номер текущей зоны платной парковки (используя externalZoneId) и ее границы на карте
1. `{"open": "MobileParkingZoneList"}`
2. `{"tap": "MobileParkingZoneDetail"}`
3. `{"expect": {"screen": "MobileParkingZoneDetail", "visible": ["mobile-parking-zone-detail.external-zone-id", "mobile-parking-zone-detail.geometry"]}}`
4. `{"expect": {"screen": "MobileParkingZoneDetail", "status": "in_zone", "visible": ["mobile-parking-zone-detail.external-zone-id", "mobile-parking-zone-detail.geometry"], "row": {"seed": "ParkingZone[0]"}}}`

## US-05 — чтобы система отображала доступные параметры парковки, включая справочную информацию о цене (priceDescription) и точные тарифы из объекта tariff.periods
1. `{"open": "MobileParkingZoneList"}`
2. `{"tap": "MobileParkingZoneDetail"}`
3. `{"expect": {"screen": "MobileParkingZoneDetail", "visible": ["mobile-parking-zone-detail.price-description", "mobile-parking-zone-detail.tariff"]}}`

## US-06 — чтобы я мог запустить или подтвердить парковочную сессию, а система хранила информацию об этой активной сессии
1. `{"open": "MobileParkingSessionList"}`
2. `{"tap": "MobileParkingSessionForm"}`
3. `{"fill": "ParkingSession.zoneId", "value": {"seed": "ParkingZone[0].externalZoneId"}}`
4. `{"fill": "ParkingSession.startedAt", "value": {"gen": "valid"}}`
5. `{"fill": "ParkingSession.endsAt", "value": {"gen": "valid"}}`
6. `{"fill": "ParkingSession.state", "value": {"seed": "ParkingSessionStatus[0]"}}`
7. `{"fill": "ParkingSession.plannedEndAt", "value": {"gen": "valid"}}`
8. `{"tap": "ParkingSession.create"}`
9. `{"expect": {"screen": "MobileParkingSessionDetail", "status": "active", "visible": ["mobile-parking-session-detail.ends-at"]}}`

## US-07 — чтобы система отображала время окончания подтвержденной парковочной сессии в мобильном приложении
1. `{"open": "MobileParkingSessionList"}`
2. `{"tap": "MobileParkingSessionDetail"}`
3. `{"expect": {"screen": "MobileParkingSessionDetail", "visible": ["mobile-parking-session-detail.planned-end-at", "mobile-parking-session-detail.ends-at", "mobile-parking-session-detail.state"], "row": {"seed": "ParkingSession[0]"}}}`

## US-08 — чтобы система отправляла мне предупреждение за 10 минут до окончания оплаченной парковочной сессии и уведомляла о необходимости проверки или новой оплаты
1. `{"open": "MobileParkingSessionList"}`
2. `{"tap": "MobileParkingSessionDetail"}`
3. `{"expect": {"screen": "MobileParkingSessionDetail", "visible": ["mobile-parking-session-detail.planned-end-at", "mobile-parking-session-detail.status"]}}`

## US-09 — чтобы мобильное приложение предоставляло мне переход по фиксированному URL к официальному сервису оплаты парковки Санкт-Петербурга
1. `{"open": "MobileParkingSessionList"}`
2. `{"tap": "MobileParkingSessionDetail"}`
3. `{"tap": "GetPaymentUrl"}`
4. `{"expect": {"screen": "MobileParkingSessionDetail"}}`

## US-10 — чтобы в мобильном приложении отображался маршрут моего движения и история всех парковочных сессий
1. `{"open": "MobileParkingZoneList"}`
2. `{"expect": {"screen": "MobileParkingZoneList", "visible": ["mobile-parking-zone-list.external-zone-id", "mobile-parking-zone-list.display-name", "mobile-parking-zone-list.geometry", "mobile-parking-zone-list.state", "mobile-parking-zone-list.price"]}}`
3. `{"tap": "MobileParkingZoneDetail"}`

Скриншоты текущего прогона не предоставлены.

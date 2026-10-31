namespace App.Domain;

public enum GeoPointType
{
}

public enum ParkingSessionState
{
    Created,
    Active,
    WarningSent,
    Expired,
    Completed,
}

public enum VehicleState
{
    OutsideZone,
    InZone,
}

public sealed class Driver
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("employeeId")]
    public string EmployeeId { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("fullName")]
    public string FullName { get; set; } = "";
    [System.Text.Json.Serialization.JsonPropertyName("name")]
    public string? Name { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("phone")]
    public string? Phone { get; set; }
}

public sealed class GeoPoint
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("latitude")]
    public decimal? Latitude { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("longitude")]
    public decimal? Longitude { get; set; }
}

public sealed class Notification
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("driverId")]
    public Guid? DriverId { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("message")]
    public string? Message { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("sentAt")]
    public DateTimeOffset? SentAt { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("sessionId")]
    public Guid? SessionId { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("type")]
    public string? Type { get; set; }
}

public sealed class NotificationType
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("values")]
    public string? Values { get; set; }
}

public sealed class ParkingEvent
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("message")]
    public string? Message { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("occurredAt")]
    public DateTimeOffset? OccurredAt { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("sessionId")]
    public Guid? SessionId { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("type")]
    public string? Type { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("zoneId")]
    public Guid? ZoneId { get; set; }
}

public sealed class ParkingEventType
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("values")]
    public string? Values { get; set; }
}

public sealed class ParkingSession
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("actualEndAt")]
    public DateTimeOffset? ActualEndAt { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("createdAt")]
    public string CreatedAt { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("endsAt")]
    public string EndsAt { get; set; } = "";
    [System.Text.Json.Serialization.JsonPropertyName("plannedEndAt")]
    public DateTimeOffset? PlannedEndAt { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("startedAt")]
    public string StartedAt { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("state")]
    public string State { get; set; } = "";
    [System.Text.Json.Serialization.JsonPropertyName("status")]
    public ParkingSessionState Status { get; set; } = ParkingSessionState.Created;
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("vehicleId")]
    public string VehicleId { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("zoneId")]
    public string ZoneId { get; set; } = "";
}

public sealed class ParkingSessionStatus
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("values")]
    public string? Values { get; set; }
}

public sealed class ParkingZone
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("displayName")]
    public string DisplayName { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("externalZoneId")]
    public string ExternalZoneId { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("geometry")]
    public string Geometry { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("initDate")]
    public string InitDate { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("lastSyncedAt")]
    public string LastSyncedAt { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("minTime")]
    public int MinTime { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("price")]
    public int Price { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("priceDescription")]
    public string PriceDescription { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("state")]
    public string State { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("tariff")]
    public string Tariff { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("timeStep")]
    public int TimeStep { get; set; }
}

public sealed class Route
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("isMock")]
    public bool? IsMock { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("name")]
    public string? Name { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("points")]
    public Guid? Points { get; set; }
}

public sealed class Tariff
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("hasHolidays")]
    public string HasHolidays { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("periods")]
    public string Periods { get; set; } = "";
}

public sealed class TariffPeriod
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("duration")]
    public string? Duration { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("from")]
    public string From { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("price")]
    public string Price { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("to")]
    public string To { get; set; } = "";
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("type")]
    public string Type { get; set; } = "";
    [System.Text.Json.Serialization.JsonPropertyName("vehicleType")]
    public Guid? VehicleType { get; set; }
}

public sealed class Vehicle
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("assignedDriverId")]
    public string? AssignedDriverId { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("currentLocation")]
    public string? CurrentLocation { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("driverId")]
    public string? DriverId { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("lastPositionAt")]
    public string? LastPositionAt { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("licensePlate")]
    public string LicensePlate { get; set; } = "";
    [System.Text.Json.Serialization.JsonPropertyName("plate")]
    public string? Plate { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("routeId")]
    public Guid? RouteId { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("status")]
    public string? Status { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("vehicleType")]
    public string VehicleType { get; set; } = "";
}

public sealed class VehicleStatus
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("values")]
    public string? Values { get; set; }
}

public sealed class VehicleType
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("values")]
    public string? Values { get; set; }
}

public sealed class WorkObject
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("address")]
    public string? Address { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("location")]
    public string? Location { get; set; }
    [System.Text.Json.Serialization.JsonRequired]
    [System.Text.Json.Serialization.JsonPropertyName("name")]
    public string Name { get; set; } = "";
}

public sealed class ZoneState
{
    public Guid Id { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("values")]
    public string? Values { get; set; }
}

public sealed record ConfirmParkingSession(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("sessionId")] string? SessionId);

public sealed record EndParkingSession(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("sessionId")] string? SessionId);

public sealed record GetActiveParkingSession(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("vehicleId")] string? VehicleId);

public sealed record GetAllVehicles(Guid Id);

public sealed record GetCurrentZone(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("vehicleId")] string? VehicleId);

public sealed record GetParkingEvents(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("vehicleId")] string? VehicleId);

public sealed record GetParkingSessionHistory(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("vehicleId")] string? VehicleId);

public sealed record GetPaymentUrl(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("sessionId")] string? SessionId);

public sealed record GetVehicleRoute(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("vehicleId")] string? VehicleId);

public sealed record GetZoneTariff(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("zoneId")] string? ZoneId);

public sealed record RenewParkingSession(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("newDuration")] string? NewDuration, [property: System.Text.Json.Serialization.JsonPropertyName("sessionId")] string? SessionId);

public sealed record ReportVehicleLocation(Guid Id, [property: System.Text.Json.Serialization.JsonPropertyName("latitude")] decimal? Latitude, [property: System.Text.Json.Serialization.JsonPropertyName("longitude")] decimal? Longitude, [property: System.Text.Json.Serialization.JsonPropertyName("timestamp")] string? Timestamp, [property: System.Text.Json.Serialization.JsonPropertyName("vehicleId")] string? VehicleId);

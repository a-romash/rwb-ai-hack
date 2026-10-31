namespace App.Domain;

/// <summary>Rule parameters from app.json params.</summary>
public static class Params
{
    public const string basis = "В данных представлены только линейные геометрии (LineString, MultiLineString), а не полигоны. Для корректной работы геолокации необходим буфер.";
    public static readonly TimeSpan payment_warning_lead_time = System.Xml.XmlConvert.ToTimeSpan("PT10M");
    public const string risk = "low";
    public const string statement = "Для определения нахождения автомобиля в зоне (REQ-05, REQ-10, REQ-11) используется проверка пересечения GPS-точки с геометрией LineString/MultiLineString из данных зон с заданным радиусом буфера (допущение: 10 метров).";
    public static readonly TimeSpan zone_detection_radius = System.Xml.XmlConvert.ToTimeSpan("PT0S");
}

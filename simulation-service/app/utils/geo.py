from math import asin, cos, pi, radians, sin, sqrt

from app.models.simulation import Coordinate

EARTH_RADIUS_KM = 6371.0


def haversine_km(origin: Coordinate, destination: Coordinate) -> float:
    lat1 = radians(origin.latitude)
    lon1 = radians(origin.longitude)
    lat2 = radians(destination.latitude)
    lon2 = radians(destination.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return round(2 * EARTH_RADIUS_KM * asin(sqrt(a)), 2)


def approximate_circle(center: Coordinate, radius_meters: int, points: int = 16) -> list[Coordinate]:
    lat_radius = radius_meters / 111_320
    lon_radius = radius_meters / (111_320 * max(cos(radians(center.latitude)), 0.1))
    coordinates: list[Coordinate] = []
    for index in range(points + 1):
        angle = 2 * pi * index / points
        coordinates.append(
            Coordinate(
                latitude=center.latitude + lat_radius * sin(angle),
                longitude=center.longitude + lon_radius * cos(angle),
            )
        )
    return coordinates

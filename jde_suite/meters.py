"""Telemetry maths for the IoT demo. Consumption factors are made-up demo constants."""
from __future__ import annotations

import math
from typing import Tuple

FUEL_PER_KM = 0.35      # fuel units per km (demo constant)
AVG_SPEED_KMH = 28.0    # used to turn distance into engine hours
MIN_HOURS_STEP = 0.05


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def advance(fuel: float, hours: float, distance_km: float) -> Tuple[float, float]:
    return fuel + distance_km * FUEL_PER_KM, hours + max(distance_km / AVG_SPEED_KMH, MIN_HOURS_STEP)

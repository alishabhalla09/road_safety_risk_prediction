import math
from dataclasses import dataclass
from typing import Any

from shapely.geometry import Point, Polygon


@dataclass
class TrajectoryPointData:
    track_id: int
    timestamp: float
    x: float
    y: float
    vx: float
    vy: float
    speed: float
    direction: str
    lane_id: int | None


class TrajectoryEngine:
    """Engine computing kinematic motion vectors, trajectory smoothing, and lane spatial association."""

    @staticmethod
    def calculate_direction_label(vx: float, vy: float) -> str:
        """Convert velocity vector (vx, vy) into cardinal direction label."""
        if abs(vx) < 1.0 and abs(vy) < 1.0:
            return "STATIONARY"

        angle = math.degrees(math.atan2(vy, vx)) % 360

        if 45 <= angle < 135:
            return "SOUTH"  # Image coordinates y grows downward
        elif 135 <= angle < 225:
            return "WEST"
        elif 225 <= angle < 315:
            return "NORTH"
        else:
            return "EAST"

    @classmethod
    def process_point(
        cls,
        track_id: int,
        timestamp: float,
        x: float,
        y: float,
        vx: float,
        vy: float,
        lanes: list[dict[str, Any]] | None = None,
        pixels_per_meter: float = 25.0
    ) -> TrajectoryPointData:
        # Speed calculation
        speed_px = math.sqrt(vx ** 2 + vy ** 2)
        speed_kmh = round((speed_px / pixels_per_meter) * 3.6, 2)
        direction = cls.calculate_direction_label(vx, vy)

        # Determine lane assignment using Point-in-Polygon check
        lane_id = None
        if lanes:
            pt = Point(x, y)
            for lane in lanes:
                poly_coords = lane.get("polygon")
                if poly_coords and len(poly_coords) >= 3:
                    poly = Polygon(poly_coords)
                    if poly.contains(pt):
                        lane_id = lane.get("lane_id")
                        break

        return TrajectoryPointData(
            track_id=track_id,
            timestamp=timestamp,
            x=round(x, 2),
            y=round(y, 2),
            vx=round(vx, 2),
            vy=round(vy, 2),
            speed=speed_kmh,
            direction=direction,
            lane_id=lane_id
        )

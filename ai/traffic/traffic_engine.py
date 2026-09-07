from dataclasses import dataclass
from typing import Any

from shapely.geometry import LineString


@dataclass
class TrafficMetricResult:
    vehicle_count: int
    density: float
    flow_in: int
    flow_out: int
    class_counts: dict[str, int]


class TrafficEngine:
    """Traffic Density and Directional Line-Crossing Flow Measurement Engine."""

    @staticmethod
    def line_intersection(
        p1: tuple[float, float],
        p2: tuple[float, float],
        line_coords: list[tuple[float, float]]
    ) -> bool:
        """Check if segment (p1 -> p2) intersects counting line segment."""
        if len(line_coords) < 2:
            return False
        movement_seg = LineString([p1, p2])
        counting_seg = LineString(line_coords[:2])
        return movement_seg.intersects(counting_seg)

    @classmethod
    def evaluate_traffic_state(
        cls,
        active_tracks: list[Any],  # List of TrackState
        camera_config: dict[str, Any],
        crossed_track_history: dict[str, set]
    ) -> TrafficMetricResult:
        vehicle_count = len(active_tracks)
        class_counts: dict[str, int] = {}
        total_vehicle_area = 0.0

        for track in active_tracks:
            cname = track.class_name
            class_counts[cname] = class_counts.get(cname, 0) + 1
            # Approximate bbox area
            box = track.bbox
            total_vehicle_area += (box[2] - box[0]) * (box[3] - box[1])

        # Compute density over total camera frame resolution or lane polygon area
        resolution = camera_config.get("resolution", {"width": 1920, "height": 1080})
        total_frame_area = float(resolution["width"] * resolution["height"])
        density = min(round(total_vehicle_area / (total_frame_area * 0.4), 4), 1.0)

        # Evaluate directional flow crossing
        counting_lines = camera_config.get("counting_lines", [])
        flow_in = 0
        flow_out = 0

        for line in counting_lines:
            line_id = line.get("line_id", "DEFAULT_LINE")
            coords = line.get("coords", [])
            inbound_direction = line.get("inbound_direction", "DOWN")

            if line_id not in crossed_track_history:
                crossed_track_history[line_id] = set()

            for track in active_tracks:
                if track.track_id in crossed_track_history[line_id]:
                    continue  # Already counted this track crossing

                if len(track.history) >= 2:
                    p1 = (track.history[-2][1], track.history[-2][2])
                    p2 = (track.history[-1][1], track.history[-1][2])

                    if cls.line_intersection(p1, p2, coords):
                        crossed_track_history[line_id].add(track.track_id)

                        # Check directional flow heading
                        if track.vy > 0 and inbound_direction == "DOWN":
                            flow_in += 1
                        elif track.vy < 0 and inbound_direction == "UP":
                            flow_in += 1
                        else:
                            flow_out += 1

        return TrafficMetricResult(
            vehicle_count=vehicle_count,
            density=density,
            flow_in=flow_in,
            flow_out=flow_out,
            class_counts=class_counts
        )

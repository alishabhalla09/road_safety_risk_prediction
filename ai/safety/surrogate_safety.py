import datetime
import math
from dataclasses import dataclass
from typing import Any

from shapely.geometry import Point, Polygon


@dataclass
class SafetyEventData:
    camera_id: str
    track_a: int
    track_b: int
    type: str  # NEAR_MISS_TTC or PET_CONFLICT
    timestamp: datetime.datetime
    ttc: float | None
    pet: float | None
    separation: float
    quality: str  # LOW, MEDIUM, HIGH


class SurrogateSafetyEngine:
    """Surrogate Safety Measures Engine evaluating Time-to-Collision (TTC) and Post-Encroachment Time (PET)."""

    def __init__(self, pixels_per_meter: float = 25.0):
        self.pixels_per_meter = pixels_per_meter
        # Zone occupation log: (camera_id, zone_id) -> List of (track_id, entry_time, exit_time)
        self.zone_occupation_history: dict[tuple[str, str], list[tuple[int, float, float | None]]] = {}
        self.triggered_events: set = set()

    def evaluate_ttc_and_pet(
        self,
        camera_id: str,
        active_tracks: list[Any],
        camera_config: dict[str, Any],
        current_time: float
    ) -> list[SafetyEventData]:
        events: list[SafetyEventData] = []
        num_tracks = len(active_tracks)

        # Step 1: Evaluate Time-to-Collision (TTC) for track pairs
        for i in range(num_tracks):
            t1 = active_tracks[i]
            for j in range(i + 1, num_tracks):
                t2 = active_tracks[j]

                # Compute spatial separation in meters
                dx = (t1.center[0] - t2.center[0]) / self.pixels_per_meter
                dy = (t1.center[1] - t2.center[1]) / self.pixels_per_meter
                separation = math.sqrt(dx ** 2 + dy ** 2)

                # Compute relative velocity (m/s)
                dvx = (t1.vx - t2.vx) / self.pixels_per_meter
                dvy = (t1.vy - t2.vy) / self.pixels_per_meter
                rel_speed = math.sqrt(dvx ** 2 + dvy ** 2)

                # Collision trajectory check: tracks approaching each other
                dot_product = (dx * dvx) + (dy * dvy)

                if rel_speed > 0.5 and dot_product < 0:
                    ttc = separation / rel_speed
                    if 0.2 <= ttc <= 2.5:
                        pair_key = (min(t1.track_id, t2.track_id), max(t1.track_id, t2.track_id), "TTC")
                        if pair_key not in self.triggered_events:
                            self.triggered_events.add(pair_key)
                            events.append(
                                SafetyEventData(
                                    camera_id=camera_id,
                                    track_a=t1.track_id,
                                    track_b=t2.track_id,
                                    type="NEAR_MISS_TTC",
                                    timestamp=datetime.datetime.utcnow(),
                                    ttc=round(ttc, 2),
                                    pet=None,
                                    separation=round(separation, 2),
                                    quality="HIGH" if ttc < 1.2 else "MEDIUM"
                                )
                            )

        # Step 2: Evaluate Post-Encroachment Time (PET) over conflict zones
        zones = camera_config.get("zones", [])
        for zone in zones:
            zid = zone.get("zone_id", "DEFAULT_ZONE")
            poly_coords = zone.get("polygon")
            if not poly_coords or len(poly_coords) < 3:
                continue

            z_poly = Polygon(poly_coords)
            z_key = (camera_id, zid)
            if z_key not in self.zone_occupation_history:
                self.zone_occupation_history[z_key] = []

            for track in active_tracks:
                pt = Point(track.center[0], track.center[1])
                is_inside = z_poly.contains(pt)
                history = self.zone_occupation_history[z_key]

                # Check existing track entry
                existing_entry = next((h for h in history if h[0] == track.track_id and h[2] is None), None)

                if is_inside and not existing_entry:
                    # New entry into zone
                    history.append((track.track_id, current_time, None))

                    # Check PET against recently exited tracks from this zone
                    for old_tid, entry_t, exit_t in history:
                        if old_tid != track.track_id and exit_t is not None:
                            pet = current_time - exit_t
                            if 0.1 <= pet <= 2.5:
                                pet_key = (min(old_tid, track.track_id), max(old_tid, track.track_id), "PET")
                                if pet_key not in self.triggered_events:
                                    self.triggered_events.add(pet_key)
                                    events.append(
                                        SafetyEventData(
                                            camera_id=camera_id,
                                            track_a=old_tid,
                                            track_b=track.track_id,
                                            type="PET_CONFLICT",
                                            timestamp=datetime.datetime.utcnow(),
                                            ttc=None,
                                            pet=round(pet, 2),
                                            separation=0.5,
                                            quality="HIGH" if pet < 1.0 else "MEDIUM"
                                        )
                                    )

                elif not is_inside and existing_entry:
                    # Track exited zone
                    idx = history.index(existing_entry)
                    history[idx] = (existing_entry[0], existing_entry[1], current_time)

        return events

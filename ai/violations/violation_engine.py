import datetime
from dataclasses import dataclass
from typing import Any

from shapely.geometry import LineString


@dataclass
class ViolationEvent:
    camera_id: str
    track_id: int
    type: str  # WRONG_WAY, LANE_VIOLATION, RED_LIGHT
    timestamp: datetime.datetime
    confidence: float
    reason: str
    evidence_id: str


class SceneViolationEngine:
    """Scene-Aware Traffic Rule Engine with Temporal Persistence Requirement."""

    def __init__(self, temporal_persistence_threshold: int = 5):
        self.temporal_persistence_threshold = temporal_persistence_threshold
        # Stores consecutive infraction counts: (track_id, violation_type) -> count
        self.infraction_counters: dict[tuple[int, str], int] = {}
        # Stores triggered violations to prevent duplicate reporting: (track_id, violation_type) -> bool
        self.triggered_violations: set = set()

    def evaluate_frame_rules(
        self,
        camera_id: str,
        active_tracks: list[Any],
        camera_config: dict[str, Any],
        signal_state: str = "RED"
    ) -> list[ViolationEvent]:
        events: list[ViolationEvent] = []
        lanes = camera_config.get("lanes", [])
        stop_lines = camera_config.get("stop_lines", [])

        for track in active_tracks:
            tid = track.track_id

            # Rule 1: Wrong-Way Motion Check
            if hasattr(track, "lane_id") and track.lane_id is not None:
                current_lane = next((lane for lane in lanes if lane.get("lane_id") == track.lane_id), None)
                if current_lane:
                    legal_dir = current_lane.get("legal_direction", "THROUGH")
                    if (legal_dir in ["SOUTH", "DOWN"] and track.vy < -5.0) or \
                       (legal_dir in ["NORTH", "UP"] and track.vy > 5.0):
                        key = (tid, "WRONG_WAY")
                        cnt = self.infraction_counters.get(key, 0) + 1
                        self.infraction_counters[key] = cnt

                        if cnt >= self.temporal_persistence_threshold and key not in self.triggered_violations:
                            self.triggered_violations.add(key)
                            events.append(
                                ViolationEvent(
                                    camera_id=camera_id,
                                    track_id=tid,
                                    type="WRONG_WAY",
                                    timestamp=datetime.datetime.utcnow(),
                                    confidence=0.92,
                                    reason=f"Vehicle (Track {tid}) moving in opposite direction to legal lane mandate '{legal_dir}' for {cnt} frames.",
                                    evidence_id=f"ev_wrongway_{tid}_{int(datetime.datetime.utcnow().timestamp())}"
                                )
                            )

            # Rule 2: Red-Light Stop Line Crossing Check
            if signal_state == "RED" and stop_lines and len(track.history) >= 2:
                p1 = (track.history[-2][1], track.history[-2][2])
                p2 = (track.history[-1][1], track.history[-1][2])
                movement = LineString([p1, p2])

                for sline in stop_lines:
                    coords = sline.get("coords", [])
                    if len(coords) >= 2:
                        stop_seg = LineString(coords[:2])
                        if movement.intersects(stop_seg):
                            key = (tid, "RED_LIGHT")
                            if key not in self.triggered_violations:
                                self.triggered_violations.add(key)
                                events.append(
                                    ViolationEvent(
                                        camera_id=camera_id,
                                        track_id=tid,
                                        type="RED_LIGHT",
                                        timestamp=datetime.datetime.utcnow(),
                                        confidence=0.95,
                                        reason=f"Vehicle (Track {tid}) crossed stop line '{sline.get('line_id')}' while signal state was RED.",
                                        evidence_id=f"ev_redlight_{tid}_{int(datetime.datetime.utcnow().timestamp())}"
                                    )
                                )

        return events

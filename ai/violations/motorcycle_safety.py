import datetime
from typing import Any

from ai.violations.violation_engine import ViolationEvent


class MotorcycleSafetyEngine:
    """Motorcycle Safety Compliance Engine analyzing Helmet and Triple Riding infractions."""

    def __init__(self, temporal_persistence_threshold: int = 3):
        self.temporal_persistence_threshold = temporal_persistence_threshold
        self.infraction_counters = {}
        self.triggered_violations = set()

    def evaluate_motorcycle_safety(
        self,
        camera_id: str,
        active_tracks: list[Any],
        frame_detections: list[Any]
    ) -> list[ViolationEvent]:
        events: list[ViolationEvent] = []

        motorcycle_tracks = [t for t in active_tracks if t.class_name in ["motorcycle", "scooter"]]
        person_detections = [d for d in frame_detections if d.class_name in ["person", "pedestrian"]]
        helmet_detections = [d for d in frame_detections if d.class_name in ["helmet"]]

        for mtrack in motorcycle_tracks:
            tid = mtrack.track_id
            mbx = mtrack.bbox

            # Spatial association: count persons overlapping motorcycle bounding box
            associated_riders = 0
            for pd in person_detections:
                # Check bounding box overlap
                if not (pd.x2 < mbx[0] or pd.x1 > mbx[2] or pd.y2 < mbx[1] or pd.y1 > mbx[3]):
                    associated_riders += 1

            # Check Triple Riding (>= 3 riders on single motorcycle)
            if associated_riders >= 3:
                key = (tid, "TRIPLE_RIDING")
                cnt = self.infraction_counters.get(key, 0) + 1
                self.infraction_counters[key] = cnt

                if cnt >= self.temporal_persistence_threshold and key not in self.triggered_violations:
                    self.triggered_violations.add(key)
                    events.append(
                        ViolationEvent(
                            camera_id=camera_id,
                            track_id=tid,
                            type="TRIPLE_RIDING",
                            timestamp=datetime.datetime.utcnow(),
                            confidence=0.88,
                            reason=f"Motorcycle (Track {tid}) detected carrying {associated_riders} riders (Triple Riding violation).",
                            evidence_id=f"ev_tripleriding_{tid}_{int(datetime.datetime.utcnow().timestamp())}"
                        )
                    )

            # Check Helmet (if riders present but no helmet detected in motorcycle region)
            if associated_riders > 0:
                has_helmet = False
                for hd in helmet_detections:
                    if not (hd.x2 < mbx[0] or hd.x1 > mbx[2] or hd.y2 < mbx[1] or hd.y1 > mbx[3]):
                        has_helmet = True
                        break

                if not has_helmet:
                    key = (tid, "HELMET")
                    cnt = self.infraction_counters.get(key, 0) + 1
                    self.infraction_counters[key] = cnt

                    if cnt >= self.temporal_persistence_threshold and key not in self.triggered_violations:
                        self.triggered_violations.add(key)
                        events.append(
                            ViolationEvent(
                                camera_id=camera_id,
                                track_id=tid,
                                type="HELMET",
                                timestamp=datetime.datetime.utcnow(),
                                confidence=0.85,
                                reason=f"Motorcycle rider (Track {tid}) detected without required safety helmet.",
                                evidence_id=f"ev_nohelmet_{tid}_{int(datetime.datetime.utcnow().timestamp())}"
                            )
                        )

        return events

import logging
from dataclasses import dataclass, field

import numpy as np

from ai.detection.yolo_detector import DetectionResult

logger = logging.getLogger("roadguard.tracker")


@dataclass
class TrackState:
    track_id: int
    class_name: str
    first_seen_frame: int
    first_seen_time: float
    last_seen_frame: int
    last_seen_time: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    center: tuple[float, float]
    confidence: float
    history: list[tuple[float, float, float]] = field(default_factory=list)  # (timestamp, x, y)
    vx: float = 0.0
    vy: float = 0.0
    missed_frames: int = 0


def calculate_iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes."""
    x_a = max(box_a[0], box_b[0])
    y_a = max(box_a[1], box_b[1])
    x_b = min(box_a[2], box_b[2])
    y_b = min(box_a[3], box_b[3])

    inter_area = max(0.0, x_b - x_a) * max(0.0, y_b - y_a)
    box_a_area = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    box_b_area = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])

    iou = inter_area / float(box_a_area + box_b_area - inter_area + 1e-6)
    return iou


class MultiObjectTracker:
    """ByteTrack / BoT-SORT style persistent multi-object tracker."""

    def __init__(self, iou_threshold: float = 0.3, max_missed_frames: int = 15):
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self.next_track_id = 1
        self.active_tracks: dict[int, TrackState] = {}

    def update(self, detections: list[DetectionResult], frame_no: int, timestamp: float) -> list[TrackState]:
        """Update tracker with frame detections and assign persistent track_ids."""
        matched_track_ids = set()
        matched_det_indices = set()

        if self.active_tracks and detections:
            track_ids = list(self.active_tracks.keys())
            iou_matrix = np.zeros((len(track_ids), len(detections)), dtype=np.float32)

            for i, tid in enumerate(track_ids):
                track = self.active_tracks[tid]
                for j, det in enumerate(detections):
                    det_box = (det.x1, det.y1, det.x2, det.y2)
                    iou = calculate_iou(track.bbox, det_box)
                    if track.class_name == det.class_name:
                        iou *= 1.2
                    iou_matrix[i, j] = iou

            while True:
                if iou_matrix.size == 0:
                    break
                max_val = float(np.max(iou_matrix))
                if max_val < self.iou_threshold:
                    break

                i_idx, j_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                tid = track_ids[i_idx]

                if tid not in matched_track_ids and j_idx not in matched_det_indices:
                    det = detections[j_idx]
                    det_box = (det.x1, det.y1, det.x2, det.y2)
                    cx, cy = (det.x1 + det.x2) / 2.0, (det.y1 + det.y2) / 2.0

                    track = self.active_tracks[tid]
                    prev_time, prev_cx, prev_cy = track.history[-1] if track.history else (timestamp, cx, cy)
                    dt = max(timestamp - prev_time, 0.001)

                    track.vx = round((cx - prev_cx) / dt, 2)
                    track.vy = round((cy - prev_cy) / dt, 2)
                    track.bbox = det_box
                    track.center = (cx, cy)
                    track.confidence = det.confidence
                    track.last_seen_frame = frame_no
                    track.last_seen_time = timestamp
                    track.missed_frames = 0
                    track.history.append((timestamp, cx, cy))

                    matched_track_ids.add(tid)
                    matched_det_indices.add(j_idx)

                iou_matrix[i_idx, :] = -1.0
                iou_matrix[:, j_idx] = -1.0

        for j, det in enumerate(detections):
            if j not in matched_det_indices:
                cx, cy = (det.x1 + det.x2) / 2.0, (det.y1 + det.y2) / 2.0
                tid = self.next_track_id
                self.next_track_id += 1

                new_track = TrackState(
                    track_id=tid,
                    class_name=det.class_name,
                    first_seen_frame=frame_no,
                    first_seen_time=timestamp,
                    last_seen_frame=frame_no,
                    last_seen_time=timestamp,
                    bbox=(det.x1, det.y1, det.x2, det.y2),
                    center=(cx, cy),
                    confidence=det.confidence,
                    history=[(timestamp, cx, cy)],
                    missed_frames=0
                )
                self.active_tracks[tid] = new_track
                matched_track_ids.add(tid)

        stale_tids = []
        for tid, track in self.active_tracks.items():
            if tid not in matched_track_ids:
                track.missed_frames += 1
                if track.missed_frames > self.max_missed_frames:
                    stale_tids.append(tid)

        for tid in stale_tids:
            del self.active_tracks[tid]

        return list(self.active_tracks.values())

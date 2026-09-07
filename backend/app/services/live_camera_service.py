import datetime
import logging
import time
from collections.abc import Generator
from typing import Any

import cv2
import numpy as np

from ai.anpr.anpr_engine import ANPREngine
from ai.common.config import ConfigLoader
from ai.detection.yolo_detector import YOLODetector
from ai.risk.risk_engine import ExplainableRiskEngine
from ai.safety.surrogate_safety import SurrogateSafetyEngine
from ai.tracking.tracker import MultiObjectTracker
from ai.traffic.traffic_engine import TrafficEngine
from ai.trajectory.trajectory_engine import TrajectoryEngine
from ai.violations.motorcycle_safety import MotorcycleSafetyEngine
from ai.violations.violation_engine import SceneViolationEngine

logger = logging.getLogger("roadguard.live_camera")


class LiveCameraService:
    """Service managing real-time live webcam / RTSP stream processing with live overlay rendering."""

    _active_sessions: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_live_metrics(cls, camera_id: str) -> dict[str, Any]:
        """Retrieve real-time telemetry metrics for active live camera stream."""
        session = cls._active_sessions.get(camera_id)
        if not session:
            return {
                "camera_id": camera_id,
                "status": "STOPPED",
                "active_vehicles": 0,
                "density": 0.0,
                "flow_in": 0,
                "flow_out": 0,
                "risk_score": 0.0,
                "risk_category": "LOW",
                "violations": [],
                "plates": [],
                "safety_events": [],
                "contributions": []
            }
        return session.get("latest_metrics", {})

    @classmethod
    def _render_simulated_cctv_frame(
        cls, frame_no: int, timestamp: float, w: int = 640, h: int = 480
    ) -> tuple[np.ndarray, list[Any]]:
        """Generate dynamic animated CCTV urban junction frame with moving cars, motorcycles, bus & auto-rickshaw."""
        from ai.detection.yolo_detector import DetectionResult

        # 1. Dark Asphalt Road Base
        frame = np.full((h, w, 3), (35, 42, 54), dtype=np.uint8)

        # Draw Vertical 2-Lane Roadway
        cv2.rectangle(frame, (160, 0), (480, h), (55, 65, 80), -1)
        # White dashed center line
        for y_dash in range(0, h, 30):
            cv2.line(frame, (320, y_dash), (320, y_dash + 15), (255, 255, 255), 2)

        # Draw Horizontal Crossroad
        cv2.rectangle(frame, (0, 180), (w, 300), (55, 65, 80), -1)
        for x_dash in range(0, w, 30):
            cv2.line(frame, (x_dash, 240), (x_dash + 15, 240), (255, 255, 255), 2)

        # Yellow Stop Lines
        cv2.line(frame, (160, 175), (318, 175), (0, 255, 255), 3)
        cv2.putText(frame, "STOP LINE A", (170, 168), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)

        cv2.line(frame, (322, 305), (480, 305), (0, 255, 255), 3)
        cv2.putText(frame, "STOP LINE B", (330, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)

        # Traffic Signal status
        signal_red = (frame_no // 90) % 2 == 0
        sig_color = (0, 0, 255) if signal_red else (0, 255, 0)
        cv2.rectangle(frame, (495, 140), (535, 175), (15, 23, 42), -1)
        cv2.circle(frame, (515, 157), 12, sig_color, -1)
        cv2.putText(frame, "RED" if signal_red else "GREEN", (495, 133), cv2.FONT_HERSHEY_SIMPLEX, 0.35, sig_color, 1)

        # Banner Title for CCTV Simulation
        cv2.putText(frame, "CCTV JUNCTION SIMULATOR - URBAN CAM #04", (20, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 225, 255), 2)

        # 2. Compute Moving Vehicle Trajectories & Detections
        detections: list[DetectionResult] = []

        vehicles_spec = [
            ("car", 210, 6, 45, 75, (220, 80, 40)),           # Car moving south in Lane 1
            ("motorcycle", 260, 10, 25, 45, (40, 220, 80)),    # Fast motorcycle moving south
            ("bus", 370, -4, 55, 110, (40, 160, 240)),         # Bus moving north in Lane 2
            ("auto_rickshaw", 430, -7, 35, 55, (0, 200, 255)), # Auto-rickshaw moving north
            ("car", 175, 5, 45, 70, (200, 40, 200)),           # Second car
        ]

        for idx, (cls_name, vx, speed_y, vw, vh, color) in enumerate(vehicles_spec):
            if speed_y > 0:
                vy = (frame_no * speed_y + idx * 90) % (h + 120) - 60
            else:
                vy = h - ((frame_no * abs(speed_y) + idx * 110) % (h + 120)) - 60

            x1, y1 = float(vx), float(vy)
            x2, y2 = float(vx + vw), float(vy + vh)

            # Draw vehicle body rectangle on simulated canvas
            ix1, iy1, ix2, iy2 = map(int, [x1, y1, x2, y2])
            cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), color, -1)
            cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), (255, 255, 255), 1)
            cv2.putText(frame, cls_name[:4].upper(), (ix1 + 2, iy1 + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

            # Add Detection Result
            detections.append(
                DetectionResult(
                    frame_no=frame_no,
                    timestamp=timestamp,
                    class_name=cls_name,
                    confidence=round(0.88 + idx * 0.02, 2),
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )
            )

        return frame, detections

    @classmethod
    def generate_live_mjpeg_stream(
        cls,
        camera_id: str = "CAM_WEBCAM_01",
        source: str = "0",  # "0" for local webcam or RTSP URL
        force_mock: bool = False
    ) -> Generator[bytes, None, None]:
        """Capture live webcam frames, run full AI analysis pipeline, draw overlays, and yield MJPEG stream bytes."""
        # Convert numeric string source to int for webcam index (0, 1, etc.)
        cv_source = int(source) if source.isdigit() else source
        is_mock_mode = (source == "mock" or not isinstance(cv_source, int))

        cap = None
        if not is_mock_mode:
            cap = cv2.VideoCapture(cv_source)
            if not cap.isOpened():
                logger.error(f"Could not open live webcam source: {source}")
                cap = None

        camera_config = ConfigLoader.get_default_camera_config()
        risk_config = ConfigLoader.get_risk_weights_config()

        detector = YOLODetector(force_mock=force_mock)
        tracker = MultiObjectTracker()
        violation_engine = SceneViolationEngine()
        motorcycle_engine = MotorcycleSafetyEngine()
        anpr_engine = ANPREngine()
        safety_engine = SurrogateSafetyEngine()
        risk_engine = ExplainableRiskEngine(risk_config)

        frame_no = 0
        start_time = time.time()
        crossed_track_history = {}

        cls._active_sessions[camera_id] = {
            "status": "RUNNING",
            "start_time": start_time,
            "latest_metrics": {}
        }

        try:
            while True:
                frame_no += 1
                timestamp = round(time.time() - start_time, 2)

                if cap is not None and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        time.sleep(0.03)
                        continue
                    dets = detector.detect_frame(frame, frame_no, timestamp)
                else:
                    # Synthetic dynamic animated CCTV junction stream generator
                    frame, sim_dets = cls._render_simulated_cctv_frame(frame_no, timestamp, w=640, h=480)
                    dets = sim_dets

                h, w = frame.shape[:2]

                # 2. Multi-Object Tracking
                active_tracks = tracker.update(dets, frame_no, timestamp)

                # 3. Trajectory & Kinematics
                for tstate in active_tracks:
                    traj_pt = TrajectoryEngine.process_point(
                        track_id=tstate.track_id,
                        timestamp=timestamp,
                        x=tstate.center[0],
                        y=tstate.center[1],
                        vx=tstate.vx,
                        vy=tstate.vy,
                        lanes=camera_config.get("lanes", [])
                    )
                    tstate.lane_id = traj_pt.lane_id

                # 4. Traffic Density & Flow
                traffic_res = TrafficEngine.evaluate_traffic_state(
                    active_tracks=active_tracks,
                    camera_config=camera_config,
                    crossed_track_history=crossed_track_history
                )

                # 5. Scene Violations & Motorcycle Compliance
                v_events = violation_engine.evaluate_frame_rules(
                    camera_id=camera_id,
                    active_tracks=active_tracks,
                    camera_config=camera_config
                )
                m_events = motorcycle_engine.evaluate_motorcycle_safety(
                    camera_id=camera_id,
                    active_tracks=active_tracks,
                    frame_detections=dets
                )
                current_violations = v_events + m_events

                # 6. ANPR Processing
                current_plates = []
                for tstate in active_tracks:
                    if tstate.class_name in ["car", "bus", "truck", "motorcycle", "auto_rickshaw"]:
                        candidate = anpr_engine.process_plate_crop(tstate.track_id, None, frame_no)
                        if candidate:
                            current_plates.append({
                                "track_id": candidate.track_id,
                                "plate_text": candidate.plate_text,
                                "confidence": candidate.ocr_confidence,
                                "frame_count": candidate.frame_count
                            })

                # 7. Surrogate Safety Measures (TTC/PET)
                s_events = safety_engine.evaluate_ttc_and_pet(
                    camera_id=camera_id,
                    active_tracks=active_tracks,
                    camera_config=camera_config,
                    current_time=timestamp
                )

                # 8. Explainable Risk Score
                risk_res = risk_engine.compute_risk(
                    camera_id=camera_id,
                    density=traffic_res.density,
                    flow_in=traffic_res.flow_in,
                    flow_out=traffic_res.flow_out,
                    violations=current_violations,
                    safety_events=s_events,
                    active_tracks=active_tracks
                )

                # Filter vehicle tracks for telemetry & HUD (ignore non-vehicle detections like person, bottle, etc. for vehicle count)
                VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle", "auto_rickshaw"}
                vehicle_tracks = [t for t in active_tracks if t.class_name in VEHICLE_CLASSES]

                # Store real-time metrics for API polling
                cls._active_sessions[camera_id]["latest_metrics"] = {
                    "camera_id": camera_id,
                    "status": "RUNNING",
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "active_vehicles": len(vehicle_tracks),
                    "density": round(traffic_res.density * 100, 1),
                    "flow_in": traffic_res.flow_in,
                    "flow_out": traffic_res.flow_out,
                    "risk_score": risk_res.score,
                    "risk_category": risk_res.category,
                    "violations": [
                        {
                            "track_id": ve.track_id,
                            "type": ve.type,
                            "reason": ve.reason,
                            "confidence": ve.confidence
                        }
                        for ve in current_violations
                    ],
                    "plates": current_plates,
                    "safety_events": [
                        {
                            "track_a": se.track_a,
                            "track_b": se.track_b,
                            "type": se.type,
                            "ttc": se.ttc,
                            "pet": se.pet
                        }
                        for se in s_events
                    ],
                    "contributions": [
                        {
                            "indicator": c.indicator,
                            "weight": c.weight,
                            "contribution": c.contribution
                        }
                        for c in risk_res.contributions
                    ]
                }

                # --- DRAW REAL-TIME VISUAL OVERLAYS ON LIVE FRAME ---
                # Draw ROI Counting Line
                cv2.line(frame, (50, int(h * 0.6)), (w - 50, int(h * 0.6)), (0, 255, 255), 2)
                cv2.putText(frame, "ROI COUNTING LINE", (60, int(h * 0.6) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

                # Draw Track Bounding Boxes, IDs, and Motion Vectors
                for tstate in active_tracks:
                    bx1, by1, bx2, by2 = map(int, tstate.bbox)
                    color = (0, 255, 0)
                    if any(ve.track_id == tstate.track_id for ve in current_violations):
                        color = (0, 0, 255)  # Red for violations

                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 2)
                    label = f"#{tstate.track_id} {tstate.class_name} ({tstate.confidence:.2f})"
                    cv2.putText(frame, label, (bx1, max(by1 - 8, 15)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)

                    # Velocity Vector Arrow
                    cx, cy = map(int, tstate.center)
                    vx_arrow = int(cx + tstate.vx * 0.2)
                    vy_arrow = int(cy + tstate.vy * 0.2)
                    cv2.arrowedLine(frame, (cx, cy), (vx_arrow, vy_arrow), (255, 255, 0), 2)

                # Draw Top HUD Banner
                stream_title = "CCTV STREAM SIM" if (is_mock_mode or cap is None) else "LIVE WEBCAM"
                hud_text = f"{stream_title} | Vehicles: {len(vehicle_tracks)} | Risk: {risk_res.score:.1f} ({risk_res.category})"
                hud_color = (0, 255, 0) if risk_res.category == "LOW" else (0, 165, 255) if risk_res.category == "MEDIUM" else (0, 0, 255)
                cv2.rectangle(frame, (0, 0), (w, 35), (15, 23, 42), -1)
                cv2.putText(frame, hud_text, (15, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, hud_color, 2)

                # Encode frame to JPEG
                ret_enc, jpeg_buf = cv2.imencode('.jpg', frame)
                if not ret_enc:
                    continue

                frame_bytes = jpeg_buf.tobytes()

                # Yield MJPEG multipart frame chunk
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                )

                time.sleep(0.03)  # Approx 30 FPS cap

        finally:
            if cap is not None and cap.isOpened():
                cap.release()
            cls._active_sessions[camera_id]["status"] = "STOPPED"

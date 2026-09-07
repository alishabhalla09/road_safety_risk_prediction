import datetime
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ai.anpr.anpr_engine import ANPREngine
from ai.common.config import ConfigLoader
from ai.detection.video_reader import VideoReader
from ai.detection.yolo_detector import YOLODetector
from ai.risk.risk_engine import ExplainableRiskEngine
from ai.safety.surrogate_safety import SurrogateSafetyEngine
from ai.tracking.tracker import MultiObjectTracker
from ai.traffic.traffic_engine import TrafficEngine
from ai.trajectory.trajectory_engine import TrajectoryEngine
from ai.violations.motorcycle_safety import MotorcycleSafetyEngine
from ai.violations.violation_engine import SceneViolationEngine
from backend.app.models import domain as models

logger = logging.getLogger("roadguard.orchestrator")


class PipelineOrchestrator:
    """Master pipeline orchestrator processing video into complete road safety & traffic intelligence."""

    @classmethod
    def run_full_analysis(
        cls,
        video_id: int,
        db: Session,
        sample_stride: int = 1,
        force_mock: bool = False
    ) -> dict[str, Any]:
        video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not video or not video.source:
            raise HTTPException(status_code=404, detail="Video not found or invalid source file")

        # Load camera scene config & risk weights
        camera_config = ConfigLoader.get_default_camera_config()
        risk_config = ConfigLoader.get_risk_weights_config()

        # Update or create camera config in DB
        cam_db = db.query(models.CameraConfig).filter(models.CameraConfig.camera_id == video.camera_id).first()
        if not cam_db:
            cam_db = models.CameraConfig(
                camera_id=video.camera_id,
                name=camera_config.get("name", "Main Junction"),
                lanes=camera_config.get("lanes", []),
                directions=camera_config.get("directions", []),
                counting_lines=camera_config.get("counting_lines", []),
                stop_lines=camera_config.get("stop_lines", []),
                zones=camera_config.get("zones", []),
                calibration=camera_config.get("calibration", {}),
                signal_config=camera_config.get("signal_config", {})
            )
            db.add(cam_db)
            db.commit()

        # Instantiate micro-service components
        reader = VideoReader(video.source)
        detector = YOLODetector(force_mock=force_mock)
        tracker = MultiObjectTracker()
        violation_engine = SceneViolationEngine()
        motorcycle_engine = MotorcycleSafetyEngine()
        anpr_engine = ANPREngine()
        safety_engine = SurrogateSafetyEngine()
        risk_engine = ExplainableRiskEngine(risk_config)

        # Clear existing analysis records for re-analysis clean state
        db.query(models.Detection).filter(models.Detection.video_id == video_id).delete()
        db.query(models.Track).filter(models.Track.video_id == video_id).delete()
        db.commit()

        total_frames = 0
        detections_to_insert = []
        crossed_track_history = {}
        all_violations = []
        all_safety_events = []
        last_traffic_result = None
        last_risk_output = None

        for frame_no, timestamp, frame_bgr in reader.read_frames():
            if frame_no % sample_stride != 0:
                continue

            total_frames += 1

            # 1. Detection
            dets = detector.detect_frame(frame_bgr, frame_no, timestamp)
            for d in dets:
                detections_to_insert.append(
                    models.Detection(
                        video_id=video_id,
                        frame_no=d.frame_no,
                        timestamp=d.timestamp,
                        class_name=d.class_name,
                        confidence=d.confidence,
                        x1=d.x1,
                        y1=d.y1,
                        x2=d.x2,
                        y2=d.y2
                    )
                )

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
            last_traffic_result = traffic_res

            # 5. Scene & Motorcycle Compliance Violations
            v_events = violation_engine.evaluate_frame_rules(
                camera_id=video.camera_id,
                active_tracks=active_tracks,
                camera_config=camera_config
            )
            m_events = motorcycle_engine.evaluate_motorcycle_safety(
                camera_id=video.camera_id,
                active_tracks=active_tracks,
                frame_detections=dets
            )
            all_violations.extend(v_events + m_events)

            # 6. ANPR Processing
            for tstate in active_tracks:
                if tstate.class_name in ["car", "bus", "truck", "motorcycle", "auto_rickshaw"]:
                    anpr_engine.process_plate_crop(tstate.track_id, None, frame_no)

            # 7. Surrogate Safety Measures (TTC & PET)
            s_events = safety_engine.evaluate_ttc_and_pet(
                camera_id=video.camera_id,
                active_tracks=active_tracks,
                camera_config=camera_config,
                current_time=timestamp
            )
            all_safety_events.extend(s_events)

            # 8. Risk Engine & Heatmap
            risk_res = risk_engine.compute_risk(
                camera_id=video.camera_id,
                density=traffic_res.density,
                flow_in=traffic_res.flow_in,
                flow_out=traffic_res.flow_out,
                violations=v_events + m_events,
                safety_events=s_events,
                active_tracks=active_tracks
            )
            last_risk_output = risk_res

        # Persist Detections to DB
        if detections_to_insert:
            db.bulk_save_objects(detections_to_insert)
            db.commit()

        # Persist Active Tracks to DB
        track_db_map = {}
        for tid, tstate in tracker.active_tracks.items():
            db_track = models.Track(
                video_id=video_id,
                camera_id=video.camera_id,
                track_id=tstate.track_id,
                class_name=tstate.class_name,
                first_seen=tstate.first_seen_time,
                last_seen=tstate.last_seen_time
            )
            db.add(db_track)
            db.commit()
            db.refresh(db_track)
            track_db_map[tstate.track_id] = db_track

            # Persist Trajectory Points
            for ts, cx, cy in tstate.history:
                pt_data = TrajectoryEngine.process_point(
                    track_id=tstate.track_id,
                    timestamp=ts,
                    x=cx,
                    y=cy,
                    vx=tstate.vx,
                    vy=tstate.vy,
                    lanes=camera_config.get("lanes", [])
                )
                db_pt = models.TrajectoryPoint(
                    track_ref=db_track.id,
                    timestamp=ts,
                    x=cx,
                    y=cy,
                    vx=tstate.vx,
                    vy=tstate.vy,
                    direction=pt_data.direction,
                    lane_id=pt_data.lane_id
                )
                db.add(db_pt)

        # Persist Traffic Metrics
        if last_traffic_result:
            db_metric = models.TrafficMetric(
                camera_id=video.camera_id,
                timestamp=datetime.datetime.utcnow(),
                vehicle_count=last_traffic_result.vehicle_count,
                density=last_traffic_result.density,
                flow_in=last_traffic_result.flow_in,
                flow_out=last_traffic_result.flow_out,
                class_counts=last_traffic_result.class_counts
            )
            db.add(db_metric)

        # Persist Violations
        db_violations = []
        for ve in all_violations:
            db_v = models.Violation(
                camera_id=ve.camera_id,
                track_id=track_db_map[ve.track_id].id if ve.track_id in track_db_map else None,
                type=ve.type,
                timestamp=ve.timestamp,
                confidence=ve.confidence,
                reason=ve.reason,
                evidence_id=ve.evidence_id,
                status="DETECTED"
            )
            db.add(db_v)
            db_violations.append(db_v)
        db.commit()

        # Persist ANPR Plate Candidates
        for tid in tracker.active_tracks.keys():
            candidate = anpr_engine.process_plate_crop(tid, None, total_frames)
            if candidate and tid in track_db_map:
                db_plate = models.VehiclePlate(
                    track_id=track_db_map[tid].id,
                    plate_text=candidate.plate_text,
                    ocr_confidence=candidate.ocr_confidence,
                    frame_count=candidate.frame_count,
                    best_evidence_id=candidate.best_evidence_id
                )
                db.add(db_plate)

        # Persist Safety Events (TTC/PET)
        for se in all_safety_events:
            db_se = models.SafetyEvent(
                camera_id=se.camera_id,
                track_a=se.track_a,
                track_b=se.track_b,
                type=se.type,
                timestamp=se.timestamp,
                ttc=se.ttc,
                pet=se.pet,
                separation=se.separation,
                quality=se.quality
            )
            db.add(db_se)

        # Persist Risk Score & Contributions
        if last_risk_output:
            db_risk = models.RiskScore(
                camera_id=video.camera_id,
                timestamp=last_risk_output.timestamp,
                score=last_risk_output.score,
                category=last_risk_output.category
            )
            db.add(db_risk)
            db.commit()
            db.refresh(db_risk)

            for contrib in last_risk_output.contributions:
                db_contrib = models.RiskContribution(
                    risk_score_id=db_risk.id,
                    indicator=contrib.indicator,
                    normalized_value=contrib.normalized_value,
                    weight=contrib.weight,
                    contribution=contrib.contribution
                )
                db.add(db_contrib)

        db.commit()

        return {
            "video_id": video_id,
            "camera_id": video.camera_id,
            "status": "COMPLETED",
            "frames_processed": total_frames,
            "detections_count": len(detections_to_insert),
            "tracks_count": len(tracker.active_tracks),
            "violations_count": len(all_violations),
            "safety_events_count": len(all_safety_events),
            "risk_score": last_risk_output.score if last_risk_output else 0.0,
            "risk_category": last_risk_output.category if last_risk_output else "LOW"
        }

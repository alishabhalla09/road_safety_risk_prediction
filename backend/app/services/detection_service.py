import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ai.detection.video_reader import VideoReader
from ai.detection.yolo_detector import YOLODetector
from backend.app.models import domain as models

logger = logging.getLogger("roadguard.detection_service")


class DetectionService:
    """Service orchestrating YOLO detection over registered videos and persisting results to DB."""

    @classmethod
    def run_video_detection(
        cls,
        video_id: int,
        db: Session,
        sample_stride: int = 1,
        force_mock: bool = False
    ) -> dict[str, Any]:
        video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not video or not video.source:
            raise HTTPException(status_code=404, detail="Video not found or invalid source file")

        # Initialize reader & detector
        try:
            reader = VideoReader(video.source)
            detector = YOLODetector(force_mock=force_mock)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize video processing: {str(e)}")

        total_frames_processed = 0
        detections_to_insert = []
        class_counter: dict[str, int] = {}

        # Clear any existing detections for re-analysis
        db.query(models.Detection).filter(models.Detection.video_id == video_id).delete()
        db.commit()

        for frame_no, timestamp, frame_bgr in reader.read_frames():
            if frame_no % sample_stride != 0:
                continue

            total_frames_processed += 1
            frame_dets = detector.detect_frame(frame_bgr, frame_no, timestamp)

            for det in frame_dets:
                db_det = models.Detection(
                    video_id=video_id,
                    frame_no=det.frame_no,
                    timestamp=det.timestamp,
                    class_name=det.class_name,
                    confidence=det.confidence,
                    x1=det.x1,
                    y1=det.y1,
                    x2=det.x2,
                    y2=det.y2,
                )
                detections_to_insert.append(db_det)
                class_counter[det.class_name] = class_counter.get(det.class_name, 0) + 1

        # Bulk insert for efficiency
        if detections_to_insert:
            db.bulk_save_objects(detections_to_insert)
            db.commit()

        logger.info(
            f"Video {video_id} analysis complete: {total_frames_processed} frames, {len(detections_to_insert)} detections saved."
        )

        return {
            "video_id": video_id,
            "camera_id": video.camera_id,
            "status": "COMPLETED",
            "total_frames_processed": total_frames_processed,
            "total_detections_saved": len(detections_to_insert),
            "class_counts": class_counter,
        }

    @classmethod
    def get_video_detections(
        cls,
        video_id: int,
        db: Session,
        class_name: str | None = None,
        min_confidence: float = 0.0,
        offset: int = 0,
        limit: int = 200
    ):
        query = db.query(models.Detection).filter(models.Detection.video_id == video_id)
        if class_name:
            query = query.filter(models.Detection.class_name == class_name)
        if min_confidence > 0.0:
            query = query.filter(models.Detection.confidence >= min_confidence)

        return query.order_by(models.Detection.frame_no.asc()).offset(offset).limit(limit).all()

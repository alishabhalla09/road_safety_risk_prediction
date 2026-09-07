import os
import tempfile

import cv2
import numpy as np
import pytest

from ai.detection.yolo_detector import DetectionResult, YOLODetector
from backend.app.models import domain as models
from backend.app.services.detection_service import DetectionService


@pytest.fixture
def test_frame():
    """Create a 640x480 RGB test image."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frame, (100, 100), (300, 300), (0, 255, 0), -1)
    return frame


@pytest.fixture
def temp_sample_video():
    """Create a 1-second synthetic MP4 video (30 frames, 640x480)."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = f.name

    width, height, fps, num_frames = 640, 480, 30.0, 30
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (50 + i * 5, 100), (200 + i * 5, 300), (255, 0, 0), -1)
        out.write(frame)

    out.release()
    yield path

    if os.path.exists(path):
        os.remove(path)


def test_yolo_detector_output_structure(test_frame):
    detector = YOLODetector(force_mock=True)
    dets = detector.detect_frame(test_frame, frame_no=1, timestamp=0.033)

    assert isinstance(dets, list)
    assert len(dets) > 0

    det = dets[0]
    assert isinstance(det, DetectionResult)
    assert isinstance(det.class_name, str)
    assert 0.0 <= det.confidence <= 1.0
    assert 0.0 <= det.x1 <= det.x2 <= 640.0
    assert 0.0 <= det.y1 <= det.y2 <= 480.0


def test_detection_service_video_run(db_session, temp_sample_video):
    # Register video in DB
    video = models.Video(
        camera_id="CAM_TEST_YOLO",
        filename="test_clip.mp4",
        source=temp_sample_video,
        fps=30.0,
        width=640,
        height=480,
        duration=1.0
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    # Run detection service
    summary = DetectionService.run_video_detection(
        video_id=video.id,
        db=db_session,
        sample_stride=1,
        force_mock=True
    )

    assert summary["status"] == "COMPLETED"
    assert summary["total_frames_processed"] == 30
    assert summary["total_detections_saved"] > 0

    # Query DB detections
    saved_dets = db_session.query(models.Detection).filter_by(video_id=video.id).all()
    assert len(saved_dets) == summary["total_detections_saved"]
    assert saved_dets[0].class_name in ["car", "motorcycle", "bus", "pedestrian", "auto_rickshaw"]


def test_analysis_start_and_get_detections_api(client, temp_sample_video):
    # 1. Upload video
    with open(temp_sample_video, "rb") as f:
        up_res = client.post(
            "/videos/upload",
            data={"camera_id": "CAM_API_DETECTION"},
            files={"file": ("clip.mp4", f, "video/mp4")}
        )
    assert up_res.status_code == 200
    video_id = up_res.json()["id"]

    # 2. Trigger analysis
    start_res = client.post(f"/analysis/start?video_id={video_id}&force_mock=true")
    assert start_res.status_code == 200
    summary = start_res.json()
    assert summary["status"] == "COMPLETED"

    # 3. Query detections
    det_res = client.get(f"/videos/{video_id}/detections?limit=50")
    assert det_res.status_code == 200
    dets_list = det_res.json()
    assert len(dets_list) > 0
    assert "x1" in dets_list[0]
    assert "y1" in dets_list[0]

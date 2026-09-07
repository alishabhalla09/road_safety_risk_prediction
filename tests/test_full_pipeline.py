import os
import tempfile

import cv2
import numpy as np
import pytest

from backend.app.models import domain as models
from backend.app.services.pipeline_orchestrator import PipelineOrchestrator


@pytest.fixture
def synthetic_traffic_video():
    """Create a 2-second synthetic MP4 traffic video clip (60 frames)."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = f.name

    width, height, fps, num_frames = 640, 480, 30.0, 60
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Vehicle 1 moving south
        cv2.rectangle(frame, (100, 50 + i * 6), (200, 150 + i * 6), (0, 255, 0), -1)
        # Vehicle 2 moving north
        cv2.rectangle(frame, (350, 400 - i * 6), (450, 480 - i * 6), (255, 0, 0), -1)
        out.write(frame)

    out.release()
    yield path

    if os.path.exists(path):
        os.remove(path)


def test_full_pipeline_orchestrator(db_session, synthetic_traffic_video):
    # Register video
    video = models.Video(
        camera_id="CAM_TEST_FULL",
        filename="traffic_clip.mp4",
        source=synthetic_traffic_video,
        fps=30.0,
        width=640,
        height=480,
        duration=2.0
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    # Run complete master pipeline
    summary = PipelineOrchestrator.run_full_analysis(
        video_id=video.id,
        db=db_session,
        sample_stride=1,
        force_mock=True
    )

    assert summary["status"] == "COMPLETED"
    assert summary["frames_processed"] == 60
    assert summary["detections_count"] > 0
    assert summary["tracks_count"] > 0
    assert "risk_score" in summary

    # Verify database table populations
    dets = db_session.query(models.Detection).filter_by(video_id=video.id).all()
    assert len(dets) > 0

    tracks = db_session.query(models.Track).filter_by(video_id=video.id).all()
    assert len(tracks) > 0

    pts = db_session.query(models.TrajectoryPoint).all()
    assert len(pts) > 0

    metrics = db_session.query(models.TrafficMetric).all()
    assert len(metrics) > 0

    risk = db_session.query(models.RiskScore).first()
    assert risk is not None
    assert 0.0 <= risk.score <= 100.0
    assert risk.category in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    contribs = db_session.query(models.RiskContribution).all()
    assert len(contribs) > 0


def test_full_api_surface(client, synthetic_traffic_video):
    # Upload video via API
    with open(synthetic_traffic_video, "rb") as f:
        up_res = client.post(
            "/videos/upload",
            data={"camera_id": "CAM_FULL_API"},
            files={"file": ("clip.mp4", f, "video/mp4")}
        )
    assert up_res.status_code == 200
    video_id = up_res.json()["id"]

    # Start full analysis
    start_res = client.post(f"/analysis/start?video_id={video_id}&force_mock=true")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "COMPLETED"

    # Query Traffic API
    traffic_res = client.get("/traffic/metrics?camera_id=CAM_FULL_API")
    assert traffic_res.status_code == 200
    assert len(traffic_res.json()) > 0

    # Query Violations API
    viol_res = client.get("/violations?camera_id=CAM_FULL_API")
    assert viol_res.status_code == 200

    # Query ANPR API
    anpr_res = client.get("/plates")
    assert anpr_res.status_code == 200

    # Query Safety API
    safety_res = client.get("/safety/events?camera_id=CAM_FULL_API")
    assert safety_res.status_code == 200

    # Query Risk Current API
    risk_res = client.get("/risk/current?camera_id=CAM_FULL_API")
    assert risk_res.status_code == 200
    assert "score" in risk_res.json()

    # Query Heatmap API
    hm_res = client.get("/risk/heatmap?camera_id=CAM_FULL_API")
    assert hm_res.status_code == 200
    assert "heatmap_matrix" in hm_res.json()

    # Generate Simulated e-Challan
    if len(viol_res.json()) > 0:
        v_id = viol_res.json()[0]["id"]
        ch_res = client.post("/challans", json={"violation_id": v_id, "vehicle_number": "KA-01-AB-1234", "type": "WRONG_WAY"})
        assert ch_res.status_code == 200
        assert ch_res.json()["status"] == "GENERATED"

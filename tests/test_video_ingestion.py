import os
import tempfile

import cv2
import numpy as np
import pytest

from ai.detection.video_reader import VideoReader


@pytest.fixture
def temp_video_file():
    """Create a temporary 2-second synthetic MP4 video (60 frames, 640x480, 30 FPS)."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = f.name

    width, height, fps, num_frames = 640, 480, 30.0, 60
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Draw moving circle across frames
        cv2.circle(frame, (50 + i * 8, 240), 20, (0, 255, 0), -1)
        out.write(frame)

    out.release()

    yield path

    if os.path.exists(path):
        os.remove(path)


def test_video_reader_metadata(temp_video_file):
    reader = VideoReader(temp_video_file)
    meta = reader.get_metadata()

    assert meta.width == 640
    assert meta.height == 480
    assert meta.fps == 30.0
    assert meta.total_frames == 60
    assert meta.duration_seconds == 2.0


def test_video_reader_frame_iteration(temp_video_file):
    reader = VideoReader(temp_video_file)
    frames = list(reader.read_frames())

    assert len(frames) == 60
    frame_no, timestamp, frame_bgr = frames[0]
    assert frame_no == 0
    assert timestamp == 0.0
    assert frame_bgr.shape == (480, 640, 3)

    last_frame_no, last_ts, _ = frames[-1]
    assert last_frame_no == 59
    assert round(last_ts, 2) == 1.97


def test_video_single_frame_extraction(temp_video_file):
    reader = VideoReader(temp_video_file)
    frame = reader.extract_single_frame(10)
    assert frame is not None
    assert frame.shape == (480, 640, 3)


def test_video_upload_api_endpoint(client, temp_video_file):
    with open(temp_video_file, "rb") as f:
        response = client.post(
            "/videos/upload",
            data={"camera_id": "CAM_TEST_INGEST"},
            files={"file": ("test_clip.mp4", f, "video/mp4")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["camera_id"] == "CAM_TEST_INGEST"
    assert data["width"] == 640
    assert data["height"] == 480
    assert data["fps"] == 30.0
    assert data["duration"] == 2.0

    video_id = data["id"]
    frame_res = client.get(f"/videos/{video_id}/frame/10")
    assert frame_res.status_code == 200
    assert frame_res.headers["content-type"] == "image/jpeg"

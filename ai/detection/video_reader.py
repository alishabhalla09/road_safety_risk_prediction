import logging
import os
from collections.abc import Generator
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger("roadguard.video_reader")


@dataclass
class VideoMetadata:
    width: int
    height: int
    fps: float
    total_frames: int
    duration_seconds: float


class VideoReader:
    """Resilient video file reader with automatic frame corruption recovery and timestamp calculation."""

    def __init__(self, video_path: str, max_consecutive_errors: int = 30):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        self.video_path = video_path
        self.max_consecutive_errors = max_consecutive_errors
        self._metadata: VideoMetadata | None = None

    def get_metadata(self) -> VideoMetadata:
        """Probe video file properties using OpenCV."""
        if self._metadata is not None:
            return self._metadata

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video file: {self.video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 30.0  # Fallback FPS default if unreadable

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0.0

        cap.release()

        self._metadata = VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            duration_seconds=round(duration, 2)
        )
        return self._metadata

    def read_frames(self, start_frame: int = 0) -> Generator[tuple[int, float, np.ndarray], None, None]:
        """Generator yielding (frame_no, timestamp_seconds, frame_bgr).

        Fault tolerance: Skips corrupt frames gracefully up to max_consecutive_errors.
        """
        metadata = self.get_metadata()
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video stream: {self.video_path}")
            return

        if start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frame_no = start_frame
        consecutive_errors = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                consecutive_errors += 1
                logger.warning(
                    f"Frame decode warning at frame {frame_no} ({consecutive_errors}/{self.max_consecutive_errors})"
                )
                frame_no += 1
                if consecutive_errors >= self.max_consecutive_errors:
                    logger.error(f"Max consecutive decode errors ({self.max_consecutive_errors}) reached. Stopping stream.")
                    break
                continue

            consecutive_errors = 0  # Reset error count on successful read
            timestamp = round(frame_no / metadata.fps, 4)
            yield frame_no, timestamp, frame
            frame_no += 1

        cap.release()

    def extract_single_frame(self, frame_no: int) -> np.ndarray | None:
        """Extract a single frame by index."""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return None

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        cap.release()

        return frame if ret and frame is not None else None

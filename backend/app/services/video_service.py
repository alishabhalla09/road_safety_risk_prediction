import os
import shutil
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from ai.detection.video_reader import VideoReader
from backend.app.models import domain as models

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
MAX_FILE_SIZE_MB = 500
STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/storage/videos"))


class VideoService:
    """Service handling video file ingestion, format validation, storage, and database registration."""

    @staticmethod
    def ensure_storage_dir():
        os.makedirs(STORAGE_DIR, exist_ok=True)

    @classmethod
    def save_and_register_video(
        cls,
        file: UploadFile,
        camera_id: str,
        db: Session
    ) -> models.Video:
        cls.ensure_storage_dir()

        filename = file.filename or "uploaded_video.mp4"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # Unique filename to avoid collision
        safe_filename = f"{uuid.uuid4().hex}_{filename}"
        target_path = os.path.join(STORAGE_DIR, safe_filename)

        try:
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to write video file to disk: {str(e)}")

        # Probe video metadata using VideoReader
        try:
            reader = VideoReader(target_path)
            meta = reader.get_metadata()
        except Exception as e:
            if os.path.exists(target_path):
                os.remove(target_path)
            raise HTTPException(status_code=400, detail=f"Corrupt or unreadable video file: {str(e)}")

        # Persist video record to DB
        video_record = models.Video(
            camera_id=camera_id,
            filename=safe_filename,
            source=target_path,
            fps=meta.fps,
            width=meta.width,
            height=meta.height,
            duration=meta.duration_seconds
        )
        db.add(video_record)
        db.commit()
        db.refresh(video_record)

        return video_record

    @classmethod
    def get_frame_bytes(cls, video_path: str, frame_no: int) -> bytes | None:
        """Extract frame as JPEG bytes for preview."""
        import cv2
        reader = VideoReader(video_path)
        frame = reader.extract_single_frame(frame_no)
        if frame is None:
            return None

        success, encoded = cv2.imencode(".jpg", frame)
        return encoded.tobytes() if success else None

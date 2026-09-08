import datetime
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.models import domain as models
from backend.app.schemas import (
    CameraConfigCreate,
    CameraConfigResponse,
    ChallanCreate,
    ChallanResponse,
    DetectionResponse,
    ExperimentResponse,
    HealthResponse,
    RiskScoreResponse,
    SafetyEventResponse,
    TrafficMetricResponse,
    VehiclePlateResponse,
    VideoResponse,
    ViolationResponse,
)
from backend.app.services.challan_service import ChallanService
from backend.app.services.detection_service import DetectionService
from backend.app.services.image_analysis_service import ImageAnalysisService
from backend.app.services.live_camera_service import LiveCameraService
from backend.app.services.pipeline_orchestrator import PipelineOrchestrator
from backend.app.services.video_service import VideoService

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """System health check endpoint returning status, version, and database connectivity."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "ok" else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        timestamp=datetime.datetime.utcnow()
    )


# --- Cameras ---
@router.get("/cameras", response_model=list[CameraConfigResponse], tags=["Cameras"])
def list_cameras(db: Session = Depends(get_db)):
    """List all camera scene configurations."""
    return db.query(models.CameraConfig).all()


@router.post("/cameras", response_model=CameraConfigResponse, tags=["Cameras"])
def create_camera(config: CameraConfigCreate, db: Session = Depends(get_db)):
    """Create or update a camera scene configuration."""
    existing = db.query(models.CameraConfig).filter(models.CameraConfig.camera_id == config.camera_id).first()
    if existing:
        for key, val in config.model_dump().items():
            setattr(existing, key, val)
        db.commit()
        db.refresh(existing)
        return existing

    db_camera = models.CameraConfig(**config.model_dump())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera


@router.get("/cameras/{camera_id}", response_model=CameraConfigResponse, tags=["Cameras"])
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    """Retrieve a specific camera configuration."""
    cam = db.query(models.CameraConfig).filter(models.CameraConfig.camera_id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera config not found")
    return cam


# --- Videos ---
@router.get("/videos", response_model=list[VideoResponse], tags=["Videos"])
def list_videos(camera_id: str | None = None, db: Session = Depends(get_db)):
    """List ingested video metadata."""
    query = db.query(models.Video)
    if camera_id:
        query = query.filter(models.Video.camera_id == camera_id)
    return query.all()


@router.get("/videos/{video_id}", response_model=VideoResponse, tags=["Videos"])
def get_video(video_id: int, db: Session = Depends(get_db)):
    """Get metadata for a specific video."""
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/videos/upload", response_model=VideoResponse, tags=["Videos"])
def upload_video(
    file: UploadFile,
    camera_id: str = Form("CAM_JUNCTION_01"),
    db: Session = Depends(get_db)
):
    """Upload a video file, probe metadata, save to disk, and register in database."""
    return VideoService.save_and_register_video(file=file, camera_id=camera_id, db=db)


@router.get("/videos/{video_id}/frame/{frame_no}", tags=["Videos"])
def get_video_frame(video_id: int, frame_no: int, db: Session = Depends(get_db)):
    """Extract a specific frame from video as JPEG image."""
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video or not video.source:
        raise HTTPException(status_code=404, detail="Video or video file source not found")

    image_bytes = VideoService.get_frame_bytes(video.source, frame_no)
    if not image_bytes:
        raise HTTPException(status_code=404, detail=f"Frame {frame_no} could not be extracted")

    return Response(content=image_bytes, media_type="image/jpeg")


# --- Live Webcam / RTSP Stream ---
@router.get("/live/stream", tags=["Live Stream"])
def live_video_stream(
    camera_id: str = "CAM_WEBCAM_01",
    source: str = "0",
    force_mock: bool = False
):
    """Stream live webcam / RTSP camera feed with real-time AI bounding box and risk overlays (MJPEG stream)."""
    return StreamingResponse(
        LiveCameraService.generate_live_mjpeg_stream(
            camera_id=camera_id,
            source=source,
            force_mock=force_mock
        ),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/live/metrics", tags=["Live Stream"])
def get_live_metrics(camera_id: str = "CAM_WEBCAM_01"):
    """Retrieve real-time telemetry metrics for active live webcam stream."""
    return LiveCameraService.get_live_metrics(camera_id=camera_id)


# --- Analysis Pipeline ---
@router.post("/analysis/start", tags=["Analysis"])
def start_analysis(
    video_id: int,
    sample_stride: int = 1,
    force_mock: bool = False,
    db: Session = Depends(get_db)
):
    """Trigger full end-to-end AI analysis pipeline for a registered video."""
    return PipelineOrchestrator.run_full_analysis(
        video_id=video_id,
        db=db,
        sample_stride=sample_stride,
        force_mock=force_mock
    )


@router.post("/analysis/image", tags=["Analysis"])
async def analyze_image_snap(
    file: UploadFile | None = None,
    db: Session = Depends(get_db)
):
    """Analyze static image snap (e.g. 2 cars facing wrong-way/head-on), compute risk score, recognize plate, & auto-cut e-Challan."""
    image_bytes = None
    if file:
        image_bytes = await file.read()

    return ImageAnalysisService.analyze_image(image_bytes=image_bytes, db=db)


@router.get("/videos/{video_id}/detections", response_model=list[DetectionResponse], tags=["Analysis"])
def get_video_detections(
    video_id: int,
    class_name: str | None = None,
    min_confidence: float = 0.0,
    offset: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """Retrieve persisted detections for a video stream."""
    return DetectionService.get_video_detections(
        video_id=video_id,
        db=db,
        class_name=class_name,
        min_confidence=min_confidence,
        offset=offset,
        limit=limit
    )


# --- Traffic Intelligence ---
@router.get("/traffic/metrics", response_model=list[TrafficMetricResponse], tags=["Traffic"])
def get_traffic_metrics(camera_id: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve traffic density and directional flow metrics."""
    query = db.query(models.TrafficMetric)
    if camera_id:
        query = query.filter(models.TrafficMetric.camera_id == camera_id)
    return query.order_by(models.TrafficMetric.timestamp.desc()).limit(limit).all()


@router.get("/traffic/density", tags=["Traffic"])
def get_traffic_density(camera_id: str, db: Session = Depends(get_db)):
    """Get current traffic density ratio for a camera."""
    metric = db.query(models.TrafficMetric).filter(models.TrafficMetric.camera_id == camera_id).order_by(models.TrafficMetric.timestamp.desc()).first()
    return {
        "camera_id": camera_id,
        "density": metric.density if metric else 0.0,
        "vehicle_count": metric.vehicle_count if metric else 0,
        "class_counts": metric.class_counts if metric else {}
    }


@router.get("/traffic/flow", tags=["Traffic"])
def get_traffic_flow(camera_id: str, db: Session = Depends(get_db)):
    """Get directional inflow and outflow counts."""
    metric = db.query(models.TrafficMetric).filter(models.TrafficMetric.camera_id == camera_id).order_by(models.TrafficMetric.timestamp.desc()).first()
    return {
        "camera_id": camera_id,
        "flow_in": metric.flow_in if metric else 0,
        "flow_out": metric.flow_out if metric else 0
    }


# --- Violations ---
@router.get("/violations", response_model=list[ViolationResponse], tags=["Violations"])
def list_violations(
    camera_id: str | None = None,
    violation_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Retrieve detected traffic violations."""
    query = db.query(models.Violation)
    if camera_id:
        query = query.filter(models.Violation.camera_id == camera_id)
    if violation_type:
        query = query.filter(models.Violation.type == violation_type)
    return query.order_by(models.Violation.timestamp.desc()).limit(limit).all()


@router.get("/violations/{violation_id}", response_model=ViolationResponse, tags=["Violations"])
def get_violation(violation_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific violation event."""
    violation = db.query(models.Violation).filter(models.Violation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation record not found")
    return violation


# --- ANPR ---
@router.get("/plates", response_model=list[VehiclePlateResponse], tags=["ANPR"])
def list_plates(limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve detected license plate candidates with temporal consensus."""
    return db.query(models.VehiclePlate).order_by(models.VehiclePlate.created_at.desc()).limit(limit).all()


@router.get("/plates/{plate_id}", response_model=VehiclePlateResponse, tags=["ANPR"])
def get_plate(plate_id: int, db: Session = Depends(get_db)):
    """Get license plate details."""
    plate = db.query(models.VehiclePlate).filter(models.VehiclePlate.id == plate_id).first()
    if not plate:
        raise HTTPException(status_code=404, detail="License plate record not found")
    return plate


# --- Safety Events (TTC / PET) ---
@router.get("/safety/events", response_model=list[SafetyEventResponse], tags=["Safety"])
def list_safety_events(camera_id: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve Time-to-Collision (TTC) and Post-Encroachment Time (PET) surrogate safety events."""
    query = db.query(models.SafetyEvent)
    if camera_id:
        query = query.filter(models.SafetyEvent.camera_id == camera_id)
    return query.order_by(models.SafetyEvent.timestamp.desc()).limit(limit).all()


# --- Risk Engine ---
@router.get("/risk/current", response_model=RiskScoreResponse | None, tags=["Risk Engine"])
def get_current_risk(camera_id: str, db: Session = Depends(get_db)):
    """Retrieve latest explainable risk score and contribution breakdown."""
    return db.query(models.RiskScore)\
        .filter(models.RiskScore.camera_id == camera_id)\
        .order_by(models.RiskScore.timestamp.desc())\
        .first()


@router.get("/risk/history", response_model=list[RiskScoreResponse], tags=["Risk Engine"])
def get_risk_history(camera_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve historical risk scores for trend analysis."""
    return db.query(models.RiskScore)\
        .filter(models.RiskScore.camera_id == camera_id)\
        .order_by(models.RiskScore.timestamp.desc())\
        .limit(limit).all()


@router.get("/risk/heatmap", tags=["Risk Engine"])
def get_risk_heatmap(camera_id: str, db: Session = Depends(get_db)):
    """Generate spatial 10x10 risk density heatmap matrix."""
    risk = db.query(models.RiskScore).filter(models.RiskScore.camera_id == camera_id).order_by(models.RiskScore.timestamp.desc()).first()
    grid = [[0.1 * ((i + j) % 5) for j in range(10)] for i in range(10)]
    if risk and risk.category == "HIGH":
        grid[4][5] = 0.9
        grid[5][5] = 0.85

    return {
        "camera_id": camera_id,
        "risk_score": risk.score if risk else 0.0,
        "category": risk.category if risk else "LOW",
        "heatmap_matrix": grid
    }


# --- e-Challan (Simulated) ---
@router.get("/challans", response_model=list[ChallanResponse], tags=["e-Challan"])
def list_challans(status: str | None = None, db: Session = Depends(get_db)):
    """Retrieve generated e-Challan simulations."""
    return ChallanService.list_challans(db=db, status=status)


@router.post("/challans", response_model=ChallanResponse, tags=["e-Challan"])
def create_challan(challan: ChallanCreate, db: Session = Depends(get_db)):
    """Generate a simulated e-Challan from a confirmed violation."""
    return ChallanService.generate_challan_from_violation(
        violation_id=challan.violation_id,
        vehicle_number=challan.vehicle_number,
        db=db,
        notes=challan.notes
    )


@router.post("/challans/direct", response_model=ChallanResponse, tags=["e-Challan"])
def issue_direct_challan(
    vehicle_number: str = Form(...),
    violation_type: str = Form("RED_LIGHT"),
    notes: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """Directly issue/cut an e-Challan for any vehicle plate number."""
    return ChallanService.issue_direct_challan(
        vehicle_number=vehicle_number,
        violation_type=violation_type,
        notes=notes,
        db=db
    )


@router.put("/challans/{challan_id}/status", response_model=ChallanResponse, tags=["e-Challan"])
def update_challan_status(challan_id: int, status: str, db: Session = Depends(get_db)):
    """Update e-Challan status (GENERATED -> UNDER_REVIEW -> RESOLVED / CANCELLED)."""
    return ChallanService.update_challan_status(challan_id=challan_id, new_status=status, db=db)


# --- Research & Benchmark Experiments ---
@router.get("/experiments", response_model=list[ExperimentResponse], tags=["Research"])
def list_experiments(db: Session = Depends(get_db)):
    """Retrieve benchmark research experiment runs (R1-R8)."""
    return db.query(models.Experiment).order_by(models.Experiment.created_at.desc()).all()


@router.post("/experiments", response_model=ExperimentResponse, tags=["Research"])
def record_experiment(
    name: str,
    dataset: str,
    model_version: str,
    parameters: dict[str, Any],
    metrics: dict[str, Any],
    notes: str | None = None,
    db: Session = Depends(get_db)
):
    """Record research experiment performance metrics."""
    exp = models.Experiment(
        name=name,
        dataset=dataset,
        model_version=model_version,
        parameters=parameters,
        metrics=metrics,
        notes=notes
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp

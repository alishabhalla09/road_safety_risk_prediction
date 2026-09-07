from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    timestamp: datetime


class VideoBase(BaseModel):
    camera_id: str
    filename: str
    source: str | None = None
    fps: float = 30.0
    width: int
    height: int
    duration: float


class VideoCreate(VideoBase):
    pass


class VideoResponse(VideoBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DetectionResponse(BaseModel):
    id: int
    video_id: int
    frame_no: int
    timestamp: float
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    model_config = ConfigDict(from_attributes=True)


class TrackResponse(BaseModel):
    id: int
    video_id: int
    camera_id: str
    track_id: int
    class_name: str
    first_seen: float
    last_seen: float

    model_config = ConfigDict(from_attributes=True)


class TrajectoryPointResponse(BaseModel):
    id: int
    track_ref: int
    timestamp: float
    x: float
    y: float
    vx: float
    vy: float
    direction: str | None = None
    lane_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class TrafficMetricResponse(BaseModel):
    id: int
    camera_id: str
    timestamp: datetime
    vehicle_count: int
    density: float
    flow_in: int
    flow_out: int
    class_counts: dict[str, int]

    model_config = ConfigDict(from_attributes=True)


class CameraConfigBase(BaseModel):
    camera_id: str
    name: str
    lanes: list[dict[str, Any]] = Field(default_factory=list)
    directions: list[dict[str, Any]] = Field(default_factory=list)
    counting_lines: list[dict[str, Any]] = Field(default_factory=list)
    stop_lines: list[dict[str, Any]] = Field(default_factory=list)
    zones: list[dict[str, Any]] = Field(default_factory=list)
    calibration: dict[str, Any] = Field(default_factory=dict)
    signal_config: dict[str, Any] = Field(default_factory=dict)


class CameraConfigCreate(CameraConfigBase):
    pass


class CameraConfigResponse(CameraConfigBase):
    id: int
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ViolationResponse(BaseModel):
    id: int
    camera_id: str
    track_id: int | None = None
    type: str
    timestamp: datetime
    confidence: float
    reason: str | None = None
    evidence_id: str | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class VehiclePlateResponse(BaseModel):
    id: int
    track_id: int
    plate_text: str
    ocr_confidence: float
    frame_count: int
    best_evidence_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallanCreate(BaseModel):
    violation_id: int
    vehicle_number: str
    type: str
    notes: str | None = None


class ChallanResponse(BaseModel):
    id: int
    violation_id: int
    challan_number: str
    vehicle_number: str
    type: str
    timestamp: datetime
    status: str
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SafetyEventResponse(BaseModel):
    id: int
    camera_id: str
    track_a: int
    track_b: int
    type: str
    timestamp: datetime
    ttc: float | None = None
    pet: float | None = None
    separation: float | None = None
    quality: str

    model_config = ConfigDict(from_attributes=True)


class RiskContributionResponse(BaseModel):
    id: int
    indicator: str
    normalized_value: float
    weight: float
    contribution: float

    model_config = ConfigDict(from_attributes=True)


class RiskScoreResponse(BaseModel):
    id: int
    camera_id: str
    timestamp: datetime
    score: float
    category: str
    contributions: list[RiskContributionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ExperimentResponse(BaseModel):
    id: int
    name: str
    dataset: str
    model_version: str
    parameters: dict[str, Any]
    metrics: dict[str, Any]
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

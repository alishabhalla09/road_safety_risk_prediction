import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.db.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    source = Column(String(255), nullable=True)
    fps = Column(Float, nullable=False, default=30.0)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    duration = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    detections = relationship("Detection", back_populates="video", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="video", cascade="all, delete-orphan")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    frame_no = Column(Integer, nullable=False, index=True)
    timestamp = Column(Float, nullable=False)
    class_name = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    x1 = Column(Float, nullable=False)
    y1 = Column(Float, nullable=False)
    x2 = Column(Float, nullable=False)
    y2 = Column(Float, nullable=False)

    video = relationship("Video", back_populates="detections")


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    camera_id = Column(String(50), nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    class_name = Column(String(50), nullable=False)
    first_seen = Column(Float, nullable=False)
    last_seen = Column(Float, nullable=False)

    video = relationship("Video", back_populates="tracks")
    trajectory_points = relationship("TrajectoryPoint", back_populates="track", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="track")
    plate = relationship("VehiclePlate", back_populates="track", uselist=False)


class TrajectoryPoint(Base):
    __tablename__ = "trajectory_points"

    id = Column(Integer, primary_key=True, index=True)
    track_ref = Column(Integer, ForeignKey("tracks.id"), nullable=False, index=True)
    timestamp = Column(Float, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    vx = Column(Float, default=0.0)
    vy = Column(Float, default=0.0)
    direction = Column(String(50), nullable=True)
    lane_id = Column(Integer, nullable=True)

    track = relationship("Track", back_populates="trajectory_points")


class TrafficMetric(Base):
    __tablename__ = "traffic_metrics"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    vehicle_count = Column(Integer, nullable=False, default=0)
    density = Column(Float, nullable=False, default=0.0)
    flow_in = Column(Integer, nullable=False, default=0)
    flow_out = Column(Integer, nullable=False, default=0)
    class_counts = Column(JSON, nullable=False, default=dict)


class CameraConfig(Base):
    __tablename__ = "camera_configs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    lanes = Column(JSON, nullable=False, default=list)
    directions = Column(JSON, nullable=False, default=list)
    counting_lines = Column(JSON, nullable=False, default=list)
    stop_lines = Column(JSON, nullable=False, default=list)
    zones = Column(JSON, nullable=False, default=list)
    calibration = Column(JSON, nullable=False, default=dict)
    signal_config = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=True)
    type = Column(String(50), nullable=False, index=True)  # WRONG_WAY, LANE_VIOLATION, RED_LIGHT, HELMET, TRIPLE_RIDING
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    confidence = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    evidence_id = Column(String(255), nullable=True)
    status = Column(String(50), default="DETECTED", nullable=False)

    track = relationship("Track", back_populates="violations")
    challan = relationship("Challan", back_populates="violation", uselist=False)


class VehiclePlate(Base):
    __tablename__ = "vehicle_plates"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False, unique=True)
    plate_text = Column(String(50), nullable=False, index=True)
    ocr_confidence = Column(Float, nullable=False)
    frame_count = Column(Integer, nullable=False, default=1)
    best_evidence_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    track = relationship("Track", back_populates="plate")


class Challan(Base):
    __tablename__ = "challans"

    id = Column(Integer, primary_key=True, index=True)
    violation_id = Column(Integer, ForeignKey("violations.id"), nullable=False, unique=True)
    challan_number = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_number = Column(String(50), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(50), default="GENERATED", nullable=False)  # GENERATED, UNDER_REVIEW, RESOLVED, CANCELLED
    notes = Column(Text, nullable=True)

    violation = relationship("Violation", back_populates="challan")


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), nullable=False, index=True)
    track_a = Column(Integer, nullable=False)
    track_b = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)  # NEAR_MISS_TTC, PET_CONFLICT
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    ttc = Column(Float, nullable=True)
    pet = Column(Float, nullable=True)
    separation = Column(Float, nullable=True)
    quality = Column(String(20), default="MEDIUM")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    score = Column(Float, nullable=False)  # 0.0 to 100.0
    category = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL

    contributions = relationship("RiskContribution", back_populates="risk_score", cascade="all, delete-orphan")


class RiskContribution(Base):
    __tablename__ = "risk_contributions"

    id = Column(Integer, primary_key=True, index=True)
    risk_score_id = Column(Integer, ForeignKey("risk_scores.id"), nullable=False, index=True)
    indicator = Column(String(50), nullable=False)
    normalized_value = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)
    contribution = Column(Float, nullable=False)

    risk_score = relationship("RiskScore", back_populates="contributions")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    dataset = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=False, default=dict)
    metrics = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    dataset = Column(String(100), nullable=False)
    metrics = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

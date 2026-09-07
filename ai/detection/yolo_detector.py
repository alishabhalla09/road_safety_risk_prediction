from dataclasses import dataclass
import os
import logging
from typing import Any
import numpy as np
import yaml

logger = logging.getLogger("roadguard.yolo_detector")

# Standard COCO to RoadGuard class mapping
COCO_CLASS_MAPPING: dict[int, str] = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    9: "traffic light",
    39: "bottle",
    41: "cup",
    56: "chair",
    63: "laptop",
    67: "cell phone"
}

CUSTOM_CLASS_MAPPING: dict[int, str] = {
    10: "auto_rickshaw",
    11: "number_plate",
}


@dataclass
class DetectionResult:
    frame_no: int
    timestamp: float
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_no": self.frame_no,
            "timestamp": self.timestamp,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "x1": round(self.x1, 2),
            "y1": round(self.y1, 2),
            "x2": round(self.x2, 2),
            "y2": round(self.y2, 2),
        }


class YOLODetector:
    """Multi-class Real-Time YOLO Object Detector using Ultralytics YOLOv8."""

    def __init__(
        self,
        config_path: str | None = None,
        conf_threshold: float = 0.30,
        iou_threshold: float = 0.45,
        force_mock: bool = False
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.force_mock = force_mock
        self.model = None

        cfg_file = config_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../configs/yolo_config.yaml")
        )
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    self.conf_threshold = cfg.get("confidence_threshold", self.conf_threshold)
                    self.iou_threshold = cfg.get("iou_threshold", self.iou_threshold)
            except Exception as e:
                logger.warning(f"Could not load YOLO config yaml: {e}")

        # Load Ultralytics YOLO model if available & not force_mock
        if not self.force_mock:
            try:
                from ultralytics import YOLO
                model_name = "yolov8n.pt"  # Use fast nano model for real-time live webcam detection
                self.model = YOLO(model_name)
                logger.info(f"Successfully loaded Ultralytics YOLO model: {model_name}")
            except Exception as e:
                logger.warning(f"Ultralytics YOLO model loading fallback: {e}")
                self.model = None

    def detect_frame(self, frame: np.ndarray, frame_no: int, timestamp: float) -> list[DetectionResult]:
        """Detect real-world objects & road users in an image frame."""
        if frame is None or frame.size == 0:
            return []

        height, width = frame.shape[:2]
        detections: list[DetectionResult] = []

        # Real YOLO Model Inference
        if self.model is not None:
            try:
                results = self.model.predict(
                    source=frame,
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    verbose=False
                )
                for res in results:
                    boxes = res.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        xyxy = box.xyxy[0].tolist()

                        class_name = COCO_CLASS_MAPPING.get(
                            cls_id,
                            CUSTOM_CLASS_MAPPING.get(cls_id, f"object_{cls_id}")
                        )

                        detections.append(
                            DetectionResult(
                                frame_no=frame_no,
                                timestamp=timestamp,
                                class_name=class_name,
                                confidence=conf,
                                x1=xyxy[0],
                                y1=xyxy[1],
                                x2=xyxy[2],
                                y2=xyxy[3],
                            )
                        )
                return detections
            except Exception as e:
                logger.error(f"Inference error on frame {frame_no}: {e}")
                return []

        # Synthetic Mock Mode (ONLY used during isolated unit tests if force_mock=True and model is None)
        if self.force_mock and self.model is None:
            sample_classes = ["car", "motorcycle", "bus"]
            for idx, cls_name in enumerate(sample_classes):
                x1 = float(50 + (idx * 110) + (frame_no * 2) % (width - 150))
                y1 = float(100 + (idx * 50))
                x2 = float(min(x1 + 100, width - 10))
                y2 = float(min(y1 + 80, height - 10))
                conf = round(0.85 + (idx * 0.02), 2)

                detections.append(
                    DetectionResult(
                        frame_no=frame_no,
                        timestamp=timestamp,
                        class_name=cls_name,
                        confidence=conf,
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                    )
                )

        return detections

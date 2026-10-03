"""
YOLO Object Detector for Drone & Aerial Object Detection.
Provides model validation, inference execution, and standardized schema output.
"""

import os
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from ultralytics import YOLO

# Add ai-engine root directory to sys.path to allow clean imports across modules
AI_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AI_ENGINE_ROOT not in sys.path:
    sys.path.insert(0, AI_ENGINE_ROOT)

from preprocessing.frame_preprocessor import FramePreprocessor, PreprocessingMeta


@dataclass
class DetectedObject:
    """Standardized representation of a single detected object."""
    object_id: Optional[int]
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # [x1, y1, x2, y2] in original pixel coords
    bbox_normalized: Tuple[float, float, float, float]  # [nx1, ny1, nx2, ny2] in [0.0, 1.0]

    def to_event_dict(self, timestamp: float) -> Dict[str, Any]:
        """Converts to the system-wide event format required by Section 6."""
        return {
            "timestamp": round(timestamp, 2),
            "object_id": self.object_id,
            "class": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": list(self.bbox)
        }


@dataclass
class DetectionFrameResult:
    """Detection results for a single processed frame."""
    timestamp: float
    frame_index: int
    detections: List[DetectedObject]
    inference_time_ms: float
    meta: PreprocessingMeta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": round(self.timestamp, 3),
            "frame_index": self.frame_index,
            "inference_time_ms": round(self.inference_time_ms, 2),
            "detection_count": len(self.detections),
            "detections": [asdict(d) for d in self.detections]
        }


class YOLODetector:
    """Inference engine wrapping YOLO models for aerial threat detection."""

    # Default COCO aerial mappings when using general pretrained models
    DEFAULT_CLASS_MAPPING = {
        "airplane": "aircraft",
        "bird": "bird",
        "drone": "drone"
    }

    def __init__(
        self,
        weights_path: str = "ai-engine/models/yolov8n.pt",
        device: str = "cpu",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        target_classes: Optional[List[str]] = None,
        custom_class_mapping: Optional[Dict[str, str]] = None
    ) -> None:
        self.weights_path = os.path.abspath(weights_path)
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.target_classes = target_classes or ["drone", "aircraft", "bird", "airplane"]
        self.class_mapping = custom_class_mapping or self.DEFAULT_CLASS_MAPPING

        self.preprocessor = FramePreprocessor(
            target_width=640,
            target_height=640,
            preserve_aspect_ratio=True
        )

        self._validate_model_path()
        self._load_model()

    def _validate_model_path(self) -> None:
        """Validates that the model weight file exists on disk."""
        if not os.path.exists(self.weights_path):
            raise FileNotFoundError(
                f"[ERROR]\n"
                f"YOLO model not found.\n\n"
                f"Expected:\n"
                f"{self.weights_path}\n\n"
                f"Please place the model in the models directory."
            )

    def _load_model(self) -> None:
        """Loads the model locally into memory."""
        try:
            self.model = YOLO(self.weights_path)
            # Warm up model with dummy input
            dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model.predict(
                dummy_input,
                device=self.device,
                verbose=False,
                conf=self.confidence_threshold
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize YOLO model from '{self.weights_path}': {e}") from e

    def detect(
        self,
        frame: np.ndarray,
        timestamp: float = 0.0,
        frame_index: int = 0
    ) -> DetectionFrameResult:
        """
        Runs object detection on a single frame.
        Maps detected coordinates back to original frame coordinates.
        """
        # Step 1: Preprocess frame
        preprocessed_frame, meta = self.preprocessor.preprocess(frame)

        # Step 2: YOLO Inference
        t_start = time.perf_counter()
        results = self.model.predict(
            preprocessed_frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False
        )
        inference_time_ms = (time.perf_counter() - t_start) * 1000.0

        detections: List[DetectedObject] = []
        result = results[0]

        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            class_indices = result.boxes.cls.cpu().numpy().astype(int)
            names = result.names

            for idx, (box, conf, cls_idx) in enumerate(zip(boxes, confidences, class_indices)):
                raw_class_name = names.get(cls_idx, "unknown").lower()
                mapped_class = self.class_mapping.get(raw_class_name, raw_class_name)

                # Filter target classes if specified
                if self.target_classes and mapped_class not in self.target_classes and raw_class_name not in self.target_classes:
                    continue

                # Map coordinates from letterboxed frame back to original frame
                x1, y1, x2, y2 = self.preprocessor.map_box_to_original(
                    (float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                    meta
                )

                # Normalized coordinates relative to original frame
                orig_w = meta.original_width
                orig_h = meta.original_height
                norm_box = (
                    round(x1 / orig_w, 4),
                    round(y1 / orig_h, 4),
                    round(x2 / orig_w, 4),
                    round(y2 / orig_h, 4)
                )

                detections.append(
                    DetectedObject(
                        object_id=idx + 1,  # Temporary index until tracking assigns persistent ID
                        class_name=mapped_class,
                        confidence=float(conf),
                        bbox=(x1, y1, x2, y2),
                        bbox_normalized=norm_box
                    )
                )

        return DetectionFrameResult(
            timestamp=timestamp,
            frame_index=frame_index,
            detections=detections,
            inference_time_ms=inference_time_ms,
            meta=meta
        )

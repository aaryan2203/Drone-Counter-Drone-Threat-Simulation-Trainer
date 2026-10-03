"""
Unit & Integration Tests for Phase 1: AI Detection Pipeline.
Covers frame preprocessing, YOLO detection, error handling, visualization, and event serialization.
"""

import os
import sys
import pytest
import numpy as np
import cv2

# Add ai-engine root to Python path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
AI_ENGINE_ROOT = os.path.dirname(TESTS_DIR)
PROJECT_ROOT = os.path.dirname(AI_ENGINE_ROOT)

if AI_ENGINE_ROOT not in sys.path:
    sys.path.insert(0, AI_ENGINE_ROOT)

from preprocessing.frame_preprocessor import FramePreprocessor, PreprocessingMeta
from detection.yolo_detector import YOLODetector, DetectedObject, DetectionFrameResult
from detection.visualizer import DetectionVisualizer
from inference.pipeline import InferencePipeline


# =====================================================================
# 1. Preprocessing Tests
# =====================================================================

def test_preprocessor_valid_frame():
    """Verify that a valid 640x480 frame is correctly padded and scaled to 640x640."""
    preprocessor = FramePreprocessor(target_width=640, target_height=640, preserve_aspect_ratio=True)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    processed, meta = preprocessor.preprocess(frame)

    assert processed.shape == (640, 640, 3)
    assert meta.original_width == 640
    assert meta.original_height == 480
    assert meta.scale_factor == 1.0  # 640 width matches 640 target
    assert meta.pad_top == 80       # (640 - 480) // 2
    assert meta.pad_left == 0


def test_preprocessor_invalid_frames():
    """Verify that None, empty, or 2D single-channel arrays raise ValueError."""
    preprocessor = FramePreprocessor()

    with pytest.raises(ValueError):
        preprocessor.preprocess(None)

    with pytest.raises(ValueError):
        preprocessor.preprocess(np.array([], dtype=np.uint8))

    with pytest.raises(ValueError):
        # 2D grayscale image without 3 channels
        preprocessor.preprocess(np.zeros((100, 100), dtype=np.uint8))


def test_preprocessor_coordinate_mapping():
    """Verify that bounding box coordinates in letterboxed frame map back accurately to original frame."""
    meta = PreprocessingMeta(
        original_height=480,
        original_width=640,
        target_height=640,
        target_width=640,
        scale_factor=1.0,
        pad_top=80,
        pad_left=0
    )

    # Box inside padded frame at [100, 180, 200, 280] (y is offset by 80 pad)
    orig_box = FramePreprocessor.map_box_to_original((100.0, 180.0, 200.0, 280.0), meta)

    assert orig_box == (100, 100, 200, 200)


def test_preprocessor_clahe_contrast_enhancement():
    """Verify contrast enhancement runs and preserves frame shape."""
    preprocessor = FramePreprocessor(apply_clahe=True)
    dark_frame = np.full((100, 100, 3), 30, dtype=np.uint8)

    processed, _ = preprocessor.preprocess(dark_frame)
    assert processed.shape == (640, 640, 3)
    assert processed.dtype == np.uint8


# =====================================================================
# 2. YOLO Detector Tests
# =====================================================================

def test_detector_missing_model_raises_filenotfound():
    """Verify that a clear, informative FileNotFoundError is raised if weights don't exist."""
    fake_path = "ai-engine/models/nonexistent_model.pt"
    with pytest.raises(FileNotFoundError) as exc_info:
        YOLODetector(weights_path=fake_path)

    assert "[ERROR]" in str(exc_info.value)
    assert "YOLO model not found" in str(exc_info.value)


def test_detector_inference_and_schema():
    """Verify inference execution on a synthetic frame and validate output schemas."""
    weights_path = os.path.join(AI_ENGINE_ROOT, "models", "yolov8n.pt")
    if not os.path.exists(weights_path):
        pytest.skip(f"Model file not present at {weights_path}")

    detector = YOLODetector(
        weights_path=weights_path,
        device="cpu",
        confidence_threshold=0.10
    )

    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw simple shapes
    cv2.circle(test_frame, (320, 240), 40, (200, 200, 200), -1)

    result = detector.detect(test_frame, timestamp=1.5, frame_index=10)

    assert isinstance(result, DetectionFrameResult)
    assert result.timestamp == 1.5
    assert result.frame_index == 10
    assert result.inference_time_ms > 0

    # Test event dictionary schema conformance (Section 6)
    dummy_obj = DetectedObject(
        object_id=3,
        class_name="drone",
        confidence=0.9421,
        bbox=(120, 80, 310, 240),
        bbox_normalized=(0.1875, 0.1667, 0.4844, 0.5)
    )
    event_dict = dummy_obj.to_event_dict(12.42)

    assert event_dict["timestamp"] == 12.42
    assert event_dict["object_id"] == 3
    assert event_dict["class"] == "drone"
    assert event_dict["confidence"] == 0.9421
    assert event_dict["bbox"] == [120, 80, 310, 240]


# =====================================================================
# 3. Visualizer Tests
# =====================================================================

def test_visualizer_rendering():
    """Verify visualizer overlays graphics without throwing or altering frame dimensions."""
    visualizer = DetectionVisualizer(hud_enabled=True)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    dummy_meta = PreprocessingMeta(480, 640, 640, 640, 1.0, 80, 0)
    dummy_obj = DetectedObject(
        object_id=1,
        class_name="drone",
        confidence=0.95,
        bbox=(100, 100, 200, 200),
        bbox_normalized=(0.156, 0.208, 0.312, 0.416)
    )
    result = DetectionFrameResult(
        timestamp=2.0,
        frame_index=1,
        detections=[dummy_obj],
        inference_time_ms=18.5,
        meta=dummy_meta
    )

    annotated = visualizer.render(frame, result, fps=30.0)

    assert annotated.shape == frame.shape
    assert annotated.dtype == np.uint8
    # Frame was modified (contains HUD pixels)
    assert not np.array_equal(annotated, frame)


# =====================================================================
# 4. Pipeline Integration Tests
# =====================================================================

def test_pipeline_process_frame():
    """Verify complete frame-to-event pipeline execution."""
    weights_path = os.path.join(AI_ENGINE_ROOT, "models", "yolov8n.pt")
    if not os.path.exists(weights_path):
        pytest.skip(f"Model file not present at {weights_path}")

    pipeline = InferencePipeline(
        weights_path=weights_path,
        confidence_threshold=0.20,
        device="cpu"
    )

    sample_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    annotated, result, events = pipeline.process_frame(sample_frame, timestamp=0.5, fps=28.0)

    assert isinstance(annotated, np.ndarray)
    assert isinstance(result, DetectionFrameResult)
    assert isinstance(events, list)

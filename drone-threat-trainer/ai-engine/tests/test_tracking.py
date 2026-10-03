"""
Unit & Integration Tests for Phase 2: Object Tracking Pipeline.
Covers Kalman filter state estimation, ByteTrack multi-object association,
track state lifecycle, persistent ID preservation across occlusions, and event schemas.
"""

import os
import sys
import pytest
import numpy as np

# Ensure ai-engine is in sys.path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
AI_ENGINE_ROOT = os.path.dirname(TESTS_DIR)
if AI_ENGINE_ROOT not in sys.path:
    sys.path.insert(0, AI_ENGINE_ROOT)

from tracking.kalman_filter import KalmanFilter
from tracking.byte_tracker import ByteTracker, STrack, TrackState, bbox_iou
from detection.yolo_detector import DetectedObject
from inference.pipeline import InferencePipeline


# =====================================================================
# 1. Kalman Filter Tests
# =====================================================================

def test_kalman_filter_initiate_and_predict():
    """Verify that Kalman filter initiates and predicts constant velocity motion."""
    kf = KalmanFilter()
    measurement = np.array([100.0, 200.0, 1.5, 40.0], dtype=np.float32)

    mean, cov = kf.initiate(measurement)
    assert mean.shape == (8,)
    assert cov.shape == (8, 8)
    assert mean[0] == 100.0
    assert mean[1] == 200.0

    # Prediction step
    pred_mean, pred_cov = kf.predict(mean, cov)
    assert pred_mean.shape == (8,)
    assert pred_cov.shape == (8, 8)


def test_kalman_filter_update():
    """Verify that Kalman filter updates state distribution with a new observation."""
    kf = KalmanFilter()
    m1 = np.array([100.0, 200.0, 1.5, 40.0], dtype=np.float32)
    mean, cov = kf.initiate(m1)

    m2 = np.array([105.0, 205.0, 1.5, 40.0], dtype=np.float32)
    pred_mean, pred_cov = kf.predict(mean, cov)
    upd_mean, upd_cov = kf.update(pred_mean, pred_cov, m2)

    assert upd_mean.shape == (8,)
    # Updated position should move towards measurement m2
    assert upd_mean[0] > 100.0
    assert upd_mean[1] > 200.0


# =====================================================================
# 2. STrack Tests
# =====================================================================

def test_strack_initialization_and_properties():
    """Verify STrack initialization, ID assignment, and trajectory tracking."""
    STrack.reset_id_counter(0)
    track = STrack(tlbr=(50, 50, 150, 150), score=0.92, class_name="drone", trajectory_length=10)

    assert track.track_id == 1
    assert track.class_name == "drone"
    assert track.score == 0.92
    assert len(track.trajectory) == 1
    assert track.trajectory[0] == (100, 100)  # center of 50..150

    # Update track at new position
    track.predict()
    track.update(tlbr=(55, 52, 155, 152), score=0.94)

    assert track.hits == 2
    assert track.state == TrackState.Tracked
    assert len(track.trajectory) == 2


def test_strack_event_dict_schema():
    """Verify STrack emits compliant event schema matching Section 6 & 13."""
    STrack.reset_id_counter(2)
    track = STrack(tlbr=(120, 80, 310, 240), score=0.94, class_name="drone")
    event = track.to_event_dict(timestamp=12.42, session_id="SES_001")

    assert event["session_id"] == "SES_001"
    assert event["timestamp"] == 12.42
    assert event["event"] == "object_tracked"
    assert event["object_id"] == 3
    assert event["class"] == "drone"
    assert event["confidence"] == 0.94
    assert len(event["bbox"]) == 4
    assert "velocity" in event


# =====================================================================
# 3. ByteTracker Association & Persistence Tests
# =====================================================================

def test_bytetracker_persistent_id():
    """Verify that an object tracked across multiple consecutive frames retains its ID."""
    tracker = ByteTracker(track_thresh=0.25, min_hits=1)
    tracker.reset()

    # Frame 1: Drone at (100, 100, 160, 160)
    det_f1 = [DetectedObject(None, "drone", 0.90, (100, 100, 160, 160), (0.1, 0.1, 0.2, 0.2))]
    tracks_f1 = tracker.update(det_f1, timestamp=0.0)
    assert len(tracks_f1) == 1
    initial_id = tracks_f1[0].track_id

    # Frame 2: Drone moved slightly to (104, 102, 164, 162)
    det_f2 = [DetectedObject(None, "drone", 0.92, (104, 102, 164, 162), (0.1, 0.1, 0.2, 0.2))]
    tracks_f2 = tracker.update(det_f2, timestamp=0.033)
    assert len(tracks_f2) == 1
    assert tracks_f2[0].track_id == initial_id  # PERSISTENT ID PRESERVED!

    # Frame 3: Drone continued to (108, 104, 168, 164)
    det_f3 = [DetectedObject(None, "drone", 0.89, (108, 104, 168, 164), (0.1, 0.1, 0.2, 0.2))]
    tracks_f3 = tracker.update(det_f3, timestamp=0.066)
    assert len(tracks_f3) == 1
    assert tracks_f3[0].track_id == initial_id


def test_bytetracker_multiple_objects_distinct_ids():
    """Verify that multiple targets get distinct persistent IDs."""
    tracker = ByteTracker(track_thresh=0.25, min_hits=1)
    tracker.reset()

    # Two drones far apart
    dets = [
        DetectedObject(None, "drone", 0.95, (50, 50, 110, 110), (0.1, 0.1, 0.2, 0.2)),
        DetectedObject(None, "drone", 0.88, (400, 300, 460, 360), (0.6, 0.6, 0.7, 0.7))
    ]
    tracks = tracker.update(dets, timestamp=0.0)
    assert len(tracks) == 2
    assert tracks[0].track_id != tracks[1].track_id


def test_bytetracker_occlusion_recovery():
    """
    Verify that if a detection drops for 1-2 frames (simulating occlusion / sensor glitch),
    the tracker preserves the track state in lost_stracks and re-associates with the SAME ID upon recovery.
    """
    tracker = ByteTracker(track_thresh=0.25, track_buffer=10, min_hits=1)
    tracker.reset()

    # Step 1: Initialize track
    det1 = [DetectedObject(None, "drone", 0.90, (200, 200, 260, 260), (0.3, 0.3, 0.4, 0.4))]
    t1 = tracker.update(det1, timestamp=0.0)
    assert len(t1) == 1
    drone_id = t1[0].track_id

    # Step 2: Occlusion occurs (no detections detected for 2 frames)
    t2 = tracker.update([], timestamp=0.033)
    assert len(t2) == 0
    assert len(tracker.lost_stracks) == 1  # Retained in lost pool

    t3 = tracker.update([], timestamp=0.066)
    assert len(t3) == 0
    assert len(tracker.lost_stracks) == 1

    # Step 3: Drone reappears at projected location
    det_recovered = [DetectedObject(None, "drone", 0.85, (206, 204, 266, 264), (0.3, 0.3, 0.4, 0.4))]
    t4 = tracker.update(det_recovered, timestamp=0.10)

    assert len(t4) == 1
    # MUST PRESERVE SAME PERSISTENT ID
    assert t4[0].track_id == drone_id


# =====================================================================
# 4. End-to-End Pipeline Tracking Integration
# =====================================================================

def test_pipeline_tracking_integration():
    """Verify that InferencePipeline processes frames with ByteTracker enabled."""
    weights_path = os.path.join(AI_ENGINE_ROOT, "models", "yolov8n.pt")
    if not os.path.exists(weights_path):
        pytest.skip("Model weights not present")

    pipeline = InferencePipeline(
        weights_path=weights_path,
        confidence_threshold=0.10,
        enable_tracking=True
    )
    pipeline.reset_tracker("SES_TEST")

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    annotated, result, events = pipeline.process_frame(frame, timestamp=0.1, fps=30.0)

    assert isinstance(annotated, np.ndarray)
    assert isinstance(events, list)

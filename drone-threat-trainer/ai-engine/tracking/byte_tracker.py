"""
ByteTrack Multi-Object Tracker for Persistent Aerial Threat Tracking.
Implements two-stage association, Kalman filtering, track life-cycle management,
trajectory breadcrumb recording, and velocity vector calculation.
"""

from collections import deque
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from scipy.optimize import linear_sum_assignment

from .kalman_filter import KalmanFilter


class TrackState(Enum):
    New = 0
    Tracked = 1
    Lost = 2
    Removed = 3


def bbox_iou(boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
    """Calculates pairwise Intersection-over-Union (IOU) between two sets of [x1, y1, x2, y2] boxes."""
    if len(boxes1) == 0 or len(boxes2) == 0:
        return np.zeros((len(boxes1), len(boxes2)), dtype=np.float32)

    b1_x1, b1_y1, b1_x2, b1_y2 = boxes1[:, 0], boxes1[:, 1], boxes1[:, 2], boxes1[:, 3]
    b2_x1, b2_y1, b2_x2, b2_y2 = boxes2[:, 0], boxes2[:, 1], boxes2[:, 2], boxes2[:, 3]

    inter_x1 = np.maximum(b1_x1[:, None], b2_x1)
    inter_y1 = np.maximum(b1_y1[:, None], b2_y1)
    inter_x2 = np.minimum(b1_x2[:, None], b2_x2)
    inter_y2 = np.minimum(b1_y2[:, None], b2_y2)

    inter_w = np.maximum(0.0, inter_x2 - inter_x1)
    inter_h = np.maximum(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    b1_area = (b1_x2 - b1_x1) * (b1_y2 - b1_y1)
    b2_area = (b2_x2 - b2_x1) * (b2_y2 - b2_y1)

    union = b1_area[:, None] + b2_area - inter_area
    iou = inter_area / np.maximum(union, 1e-6)
    return iou


class STrack:
    """Represents a single persistent object track."""

    _count = 0

    def __init__(
        self,
        tlbr: Tuple[int, int, int, int],
        score: float,
        class_name: str,
        trajectory_length: int = 30
    ) -> None:
        STrack._count += 1
        self.track_id = STrack._count
        self.state = TrackState.New

        self.kalman_filter = KalmanFilter()
        self.mean: Optional[np.ndarray] = None
        self.covariance: Optional[np.ndarray] = None

        self.score = score
        self.class_name = class_name
        self.hits = 1
        self.age = 1
        self.time_since_update = 0

        self.trajectory: deque = deque(maxlen=trajectory_length)
        self.velocity: Tuple[float, float] = (0.0, 0.0)

        # Initialize Kalman state
        measurement = self.tlbr_to_measurement(tlbr)
        self.mean, self.covariance = self.kalman_filter.initiate(measurement)

        cx = int((tlbr[0] + tlbr[2]) / 2)
        cy = int((tlbr[1] + tlbr[3]) / 2)
        self.trajectory.append((cx, cy))

    @staticmethod
    def reset_id_counter(start: int = 0) -> None:
        """Resets track ID counter (useful between sessions or tests)."""
        STrack._count = start

    @staticmethod
    def tlbr_to_measurement(tlbr: Tuple[int, int, int, int]) -> np.ndarray:
        """Converts [x1, y1, x2, y2] to [center_x, center_y, aspect_ratio, height]."""
        x1, y1, x2, y2 = tlbr
        w = max(1.0, float(x2 - x1))
        h = max(1.0, float(y2 - y1))
        cx = float(x1) + w / 2.0
        cy = float(y1) + h / 2.0
        aspect = w / h
        return np.array([cx, cy, aspect, h], dtype=np.float32)

    def to_tlbr(self) -> Tuple[int, int, int, int]:
        """Converts internal Kalman state to [x1, y1, x2, y2] bounding box."""
        if self.mean is None:
            return (0, 0, 0, 0)
        cx, cy, aspect, h = self.mean[:4]
        w = aspect * h
        x1 = int(round(cx - w / 2.0))
        y1 = int(round(cy - h / 2.0))
        x2 = int(round(cx + w / 2.0))
        y2 = int(round(cy + h / 2.0))
        return (x1, y1, x2, y2)

    def predict(self) -> None:
        """Projects track state forward by one frame."""
        if self.mean is not None and self.covariance is not None:
            self.mean, self.covariance = self.kalman_filter.predict(self.mean, self.covariance)
            # Record velocity estimate from state vector (indices 4 and 5)
            self.velocity = (float(self.mean[4]), float(self.mean[5]))

        self.age += 1
        self.time_since_update += 1

    def update(
        self,
        tlbr: Tuple[int, int, int, int],
        score: float,
        class_name: Optional[str] = None
    ) -> None:
        """Updates track with a new observation."""
        measurement = self.tlbr_to_measurement(tlbr)
        if self.mean is not None and self.covariance is not None:
            self.mean, self.covariance = self.kalman_filter.update(self.mean, self.covariance, measurement)
            self.velocity = (float(self.mean[4]), float(self.mean[5]))

        self.score = score
        if class_name:
            self.class_name = class_name
        self.hits += 1
        self.time_since_update = 0
        self.state = TrackState.Tracked

        # Append new centroid to trajectory
        box = self.to_tlbr()
        cx = int((box[0] + box[2]) / 2)
        cy = int((box[1] + box[3]) / 2)
        self.trajectory.append((cx, cy))

    def mark_lost(self) -> None:
        """Marks track as temporarily lost (missed detection)."""
        self.state = TrackState.Lost

    def mark_removed(self) -> None:
        """Marks track as permanently terminated."""
        self.state = TrackState.Removed

    def to_event_dict(self, timestamp: float, session_id: str = "SES_001") -> Dict[str, Any]:
        """Emits structured tracking event matching Section 6 & 13."""
        box = self.to_tlbr()
        return {
            "session_id": session_id,
            "timestamp": round(timestamp, 2),
            "event": "object_tracked",
            "object_id": self.track_id,
            "class": self.class_name,
            "confidence": round(self.score, 4),
            "bbox": [box[0], box[1], box[2], box[3]],
            "velocity": [round(self.velocity[0], 2), round(self.velocity[1], 2)]
        }


class ByteTracker:
    """ByteTrack algorithm implementation with two-stage association."""

    def __init__(
        self,
        track_thresh: float = 0.25,
        match_thresh: float = 0.70,
        track_buffer: int = 30,
        min_hits: int = 2,
        trajectory_length: int = 30
    ) -> None:
        self.track_thresh = track_thresh
        self.match_thresh = match_thresh
        self.track_buffer = track_buffer
        self.min_hits = min_hits
        self.trajectory_length = trajectory_length

        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []
        self.frame_id = 0

    def reset(self) -> None:
        """Resets tracker state."""
        self.tracked_stracks.clear()
        self.lost_stracks.clear()
        self.removed_stracks.clear()
        self.frame_id = 0
        STrack.reset_id_counter(0)

    def update(
        self,
        detections: List[Any],
        timestamp: float = 0.0
    ) -> List[STrack]:
        """
        Processes new detections:
        1. Projects existing tracks via Kalman filter
        2. Stage 1: High-confidence detection matching
        3. Stage 2: Low-confidence detection recovery
        4. Track activation, loss, and cleanup
        """
        self.frame_id += 1

        # Separate detections into high-score and low-score
        det_high = []
        det_low = []
        for det in detections:
            # Supports DetectedObject or dict with bbox and confidence
            bbox = det.bbox if hasattr(det, "bbox") else det["bbox"]
            conf = det.confidence if hasattr(det, "confidence") else det["confidence"]
            cls_name = det.class_name if hasattr(det, "class_name") else det.get("class", "drone")

            item = (bbox, conf, cls_name)
            if conf >= self.track_thresh:
                det_high.append(item)
            else:
                det_low.append(item)

        # 1. Predict new locations of existing tracks
        for track in self.tracked_stracks:
            track.predict()
        for track in self.lost_stracks:
            track.predict()

        # Combine tracked and lost pools for matching
        track_pool = [t for t in self.tracked_stracks if t.state in (TrackState.Tracked, TrackState.New)]
        track_pool.extend(self.lost_stracks)

        # --- Stage 1: Match high-confidence detections ---
        matched_tracks_1, unmatched_tracks_1, unmatched_det_high = self._associate(
            track_pool, det_high, self.match_thresh
        )

        for track_idx, det_idx in matched_tracks_1:
            track = track_pool[track_idx]
            bbox, conf, cls_name = det_high[det_idx]
            track.update(bbox, conf, cls_name)
            if track in self.lost_stracks:
                self.lost_stracks.remove(track)
            if track not in self.tracked_stracks:
                self.tracked_stracks.append(track)

        # --- Stage 2: Match remaining tracks with low-confidence detections ---
        remaining_tracks = [track_pool[i] for i in unmatched_tracks_1]
        matched_tracks_2, unmatched_tracks_2, _ = self._associate(
            remaining_tracks, det_low, match_thresh=0.50
        )

        for track_idx, det_idx in matched_tracks_2:
            track = remaining_tracks[track_idx]
            bbox, conf, cls_name = det_low[det_idx]
            track.update(bbox, conf, cls_name)
            if track in self.lost_stracks:
                self.lost_stracks.remove(track)
            if track not in self.tracked_stracks:
                self.tracked_stracks.append(track)

        # --- Handle Unmatched Tracks ---
        for track_idx in unmatched_tracks_2:
            track = remaining_tracks[track_idx]
            if track.state != TrackState.Lost:
                track.mark_lost()
                if track in self.tracked_stracks:
                    self.tracked_stracks.remove(track)
                if track not in self.lost_stracks:
                    self.lost_stracks.append(track)

        # --- Initialize New Tracks from Unmatched High-Confidence Detections ---
        for det_idx in unmatched_det_high:
            bbox, conf, cls_name = det_high[det_idx]
            new_track = STrack(bbox, conf, cls_name, trajectory_length=self.trajectory_length)
            if self.min_hits <= 1 or self.frame_id <= self.min_hits:
                new_track.state = TrackState.Tracked
            self.tracked_stracks.append(new_track)

        # --- Clean up dead lost tracks ---
        active_lost: List[STrack] = []
        for track in self.lost_stracks:
            if track.time_since_update > self.track_buffer:
                track.mark_removed()
                self.removed_stracks.append(track)
            else:
                active_lost.append(track)
        self.lost_stracks = active_lost

        # Return confirmed active tracks visible in this frame
        confirmed_tracks = [
            t for t in self.tracked_stracks
            if t.state == TrackState.Tracked and t.time_since_update == 0 and (t.hits >= self.min_hits or self.frame_id <= self.min_hits)
        ]
        return confirmed_tracks

    def _associate(
        self,
        tracks: List[STrack],
        detections: List[Tuple],
        match_thresh: float
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Associates tracks and detections via IOU and Hungarian algorithm."""
        if len(tracks) == 0 or len(detections) == 0:
            return [], list(range(len(tracks))), list(range(len(detections)))

        track_boxes = np.array([t.to_tlbr() for t in tracks], dtype=np.float32)
        det_boxes = np.array([d[0] for d in detections], dtype=np.float32)

        ious = bbox_iou(track_boxes, det_boxes)
        # Cost is 1.0 - IOU
        cost_matrix = 1.0 - ious

        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        matched_indices = []
        unmatched_tracks = set(range(len(tracks)))
        unmatched_dets = set(range(len(detections)))

        for r, c in zip(row_indices, col_indices):
            # Check if IOU is above threshold (cost <= 1.0 - match_thresh)
            if ious[r, c] >= match_thresh:
                matched_indices.append((r, c))
                unmatched_tracks.discard(r)
                unmatched_dets.discard(c)

        return matched_indices, sorted(list(unmatched_tracks)), sorted(list(unmatched_dets))

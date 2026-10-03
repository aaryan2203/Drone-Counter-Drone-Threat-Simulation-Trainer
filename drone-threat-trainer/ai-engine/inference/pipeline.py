"""
AI Perception & Tracking Inference Pipeline.
Integrates input sources (Camera, Recorded Video, Synthetic / Simulation Stream),
YOLO detection, ByteTrack persistent multi-object tracking, tactical visualization,
and structured event generation.
"""

import os
import sys
import time
import json
from typing import Optional, Dict, Any, Tuple, List, Callable
import cv2
import numpy as np

# Ensure ai-engine root is in path
AI_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AI_ENGINE_ROOT not in sys.path:
    sys.path.insert(0, AI_ENGINE_ROOT)

from detection.yolo_detector import YOLODetector, DetectionFrameResult
from detection.visualizer import DetectionVisualizer
from tracking.byte_tracker import ByteTracker, STrack


class InferencePipeline:
    """End-to-end detection, tracking, and event-generation pipeline."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        weights_path: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        device: str = "cpu",
        enable_tracking: bool = True
    ) -> None:
        self.config = self._load_config(config_path)
        self.tracking_config = self._load_tracking_config()
        self.enable_tracking = enable_tracking

        # Override config parameters if explicitly provided
        w_path = weights_path or self.config.get("model", {}).get("weights_path", "ai-engine/models/yolov8n.pt")
        if not os.path.isabs(w_path):
            project_root = os.path.dirname(AI_ENGINE_ROOT)
            w_path = os.path.join(project_root, w_path)

        conf = confidence_threshold if confidence_threshold is not None else self.config.get("model", {}).get("confidence_threshold", 0.25)
        dev = device or self.config.get("model", {}).get("device", "cpu")
        target_classes = self.config.get("model", {}).get("target_classes", ["drone", "aircraft", "bird", "airplane"])

        self.detector = YOLODetector(
            weights_path=w_path,
            device=dev,
            confidence_threshold=conf,
            iou_threshold=self.config.get("model", {}).get("iou_threshold", 0.45),
            target_classes=target_classes
        )

        # ByteTrack multi-object tracker
        trk_cfg = self.tracking_config.get("tracking", {})
        self.tracker = ByteTracker(
            track_thresh=trk_cfg.get("track_thresh", conf),
            match_thresh=trk_cfg.get("match_thresh", 0.70),
            track_buffer=trk_cfg.get("track_buffer", 30),
            min_hits=trk_cfg.get("min_hits", 2),
            trajectory_length=trk_cfg.get("trajectory_length", 30)
        )

        vis_cfg = self.config.get("visualization", {})
        vis_trk_cfg = self.tracking_config.get("visualization", {})
        self.visualizer = DetectionVisualizer(
            hud_enabled=vis_cfg.get("hud_enabled", True),
            theme=vis_cfg.get("theme", "tactical_cyan"),
            box_thickness=vis_cfg.get("box_thickness", 2),
            font_scale=vis_cfg.get("font_scale", 0.5),
            custom_colors=vis_cfg.get("colors"),
            render_trajectory=vis_trk_cfg.get("render_trajectory", True),
            render_velocity_vector=vis_trk_cfg.get("render_velocity_vector", True)
        )

        self._frame_count = 0
        self.session_id = "SES_001"

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Loads detection configuration from JSON file or default."""
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)

        default_config = os.path.join(os.path.dirname(AI_ENGINE_ROOT), "configs", "detection_config.json")
        if os.path.exists(default_config):
            with open(default_config, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_tracking_config(self) -> Dict[str, Any]:
        """Loads tracking configuration."""
        trk_config_path = os.path.join(os.path.dirname(AI_ENGINE_ROOT), "configs", "tracking_config.json")
        if os.path.exists(trk_config_path):
            with open(trk_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def reset_tracker(self, session_id: str = "SES_001") -> None:
        """Resets tracker states for a new training session."""
        self.tracker.reset()
        self._frame_count = 0
        self.session_id = session_id

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float = 0.0,
        fps: float = 0.0
    ) -> Tuple[np.ndarray, DetectionFrameResult, List[Dict[str, Any]]]:
        """
        Processes a single frame:
        1. Runs YOLO detection
        2. Updates ByteTrack persistent tracks
        3. Renders tactical HUD visualization (with trajectories & IDs)
        4. Formats structured events
        Returns (annotated_frame, frame_result, event_list).
        """
        self._frame_count += 1
        frame_result = self.detector.detect(frame, timestamp=timestamp, frame_index=self._frame_count)

        active_tracks: Optional[List[STrack]] = None
        events: List[Dict[str, Any]] = []

        if self.enable_tracking:
            active_tracks = self.tracker.update(frame_result.detections, timestamp=timestamp)
            # Format tracking events as specified in Section 6 & 13
            for track in active_tracks:
                events.append(track.to_event_dict(timestamp=timestamp, session_id=self.session_id))
        else:
            events = [d.to_event_dict(timestamp) for d in frame_result.detections]

        # Render tactical HUD (using persistent tracks if tracking enabled)
        annotated_frame = self.visualizer.render(
            frame=frame,
            result=frame_result,
            fps=fps,
            active_tracks=active_tracks
        )

        return annotated_frame, frame_result, events

    def process_video(
        self,
        video_source: Any,
        output_video_path: Optional[str] = None,
        event_callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        max_frames: Optional[int] = None,
        display: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Processes a video stream from either a file path, camera index (e.g. 0), or cv2.VideoCapture.
        Can write annotated video with persistent tracks and stream events.
        """
        if isinstance(video_source, (int, str)):
            cap = cv2.VideoCapture(video_source)
        else:
            cap = video_source

        if not cap.isOpened():
            raise IOError(f"Could not open video source: {video_source}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        writer: Optional[cv2.VideoWriter] = None
        if output_video_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_video_path, fourcc, source_fps, (width, height))

        all_events: List[Dict[str, Any]] = []
        frame_idx = 0
        t0 = time.time()
        smoothed_fps = source_fps

        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                frame_idx += 1
                current_time = frame_idx / source_fps

                t_now = time.time()
                elapsed = t_now - t0
                if elapsed > 0:
                    current_fps = 1.0 / max(0.001, elapsed)
                    smoothed_fps = 0.9 * smoothed_fps + 0.1 * current_fps
                t0 = t_now

                annotated, result, events = self.process_frame(
                    frame=frame,
                    timestamp=current_time,
                    fps=smoothed_fps
                )

                if events:
                    all_events.extend(events)
                    if event_callback:
                        event_callback(events)

                if writer:
                    writer.write(annotated)

                if display:
                    try:
                        cv2.imshow("Drone Threat Trainer - AI Tracking Feed", annotated)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    except Exception:
                        pass

                if max_frames and frame_idx >= max_frames:
                    break

        finally:
            cap.release()
            if writer:
                writer.release()
            if display:
                try:
                    cv2.destroyAllWindows()
                except Exception:
                    pass

        return all_events

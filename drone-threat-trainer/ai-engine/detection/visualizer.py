"""
Tactical HUD Visualizer for Drone Detection & Tracking Feed.
Renders futuristic military/tactical HUD overlays with corner brackets,
crosshairs, persistent IDs (ID 01, ID 02), flight trajectory breadcrumbs,
velocity vectors, status banners, and telemetry.
"""

from typing import Dict, Tuple, List, Optional
import cv2
import numpy as np

from .yolo_detector import DetectionFrameResult, DetectedObject


class DetectionVisualizer:
    """Renders tactical HUD graphics, tracking IDs, and trajectory trails onto video frames."""

    DEFAULT_COLORS: Dict[str, Tuple[int, int, int]] = {
        "drone": (0, 255, 255),      # Neon Yellow / Amber (BGR)
        "aircraft": (255, 180, 0),   # Cyan / Light Blue
        "airplane": (255, 180, 0),
        "bird": (0, 220, 100),       # Emerald Green
        "default": (0, 255, 0)       # Standard Green
    }

    def __init__(
        self,
        hud_enabled: bool = True,
        theme: str = "tactical_cyan",
        box_thickness: int = 2,
        font_scale: float = 0.5,
        custom_colors: Optional[Dict[str, List[int]]] = None,
        render_trajectory: bool = True,
        render_velocity_vector: bool = True
    ) -> None:
        self.hud_enabled = hud_enabled
        self.theme = theme
        self.box_thickness = box_thickness
        self.font_scale = font_scale
        self.render_trajectory = render_trajectory
        self.render_velocity_vector = render_velocity_vector

        self.colors: Dict[str, Tuple[int, int, int]] = dict(self.DEFAULT_COLORS)
        if custom_colors:
            for k, v in custom_colors.items():
                if len(v) == 3:
                    self.colors[k] = (int(v[0]), int(v[1]), int(v[2]))

    def _draw_corner_brackets(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        color: Tuple[int, int, int],
        line_len: int = 14,
        thickness: int = 2
    ) -> None:
        """Draws tactical corner brackets around the bounding box."""
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1

        cur_len = min(line_len, w // 3, h // 3)
        if cur_len <= 0:
            cur_len = 5

        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + cur_len, y1), color, thickness)
        cv2.line(frame, (x1, y1), (x1, y1 + cur_len), color, thickness)

        # Top-Right
        cv2.line(frame, (x2, y1), (x2 - cur_len, y1), color, thickness)
        cv2.line(frame, (x2, y1), (x2, y1 + cur_len), color, thickness)

        # Bottom-Left
        cv2.line(frame, (x1, y2), (x1 + cur_len, y2), color, thickness)
        cv2.line(frame, (x1, y2), (x1, y2 - cur_len), color, thickness)

        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - cur_len, y2), color, thickness)
        cv2.line(frame, (x2, y2), (x2, y2 - cur_len), color, thickness)

    def _draw_crosshair(
        self,
        frame: np.ndarray,
        center: Tuple[int, int],
        color: Tuple[int, int, int],
        radius: int = 6
    ) -> None:
        """Draws a subtle tactical crosshair at the center of the target."""
        cx, cy = center
        cv2.circle(frame, (cx, cy), radius, color, 1)
        cv2.line(frame, (cx - radius - 3, cy), (cx + radius + 3, cy), color, 1)
        cv2.line(frame, (cx, cy - radius - 3), (cx, cy + radius + 3), color, 1)

    def _draw_trajectory(
        self,
        frame: np.ndarray,
        trajectory: List[Tuple[int, int]],
        color: Tuple[int, int, int]
    ) -> None:
        """Draws a fading breadcrumb trail of past locations."""
        if len(trajectory) < 2:
            return

        pts = list(trajectory)
        n = len(pts)
        for i in range(1, n):
            # Alpha gradient: older points are fainter
            factor = i / float(n)
            thickness = 1 if factor < 0.5 else 2
            # Interpolate towards darker trail
            trail_color = (
                int(color[0] * factor * 0.8),
                int(color[1] * factor * 0.8),
                int(color[2] * factor * 0.8)
            )
            cv2.line(frame, pts[i - 1], pts[i], trail_color, thickness, cv2.LINE_AA)
            if i % 3 == 0:
                cv2.circle(frame, pts[i], 2, trail_color, -1)

    def _draw_velocity_vector(
        self,
        frame: np.ndarray,
        center: Tuple[int, int],
        velocity: Tuple[float, float],
        color: Tuple[int, int, int],
        scale: float = 2.5
    ) -> None:
        """Draws heading/velocity vector arrow."""
        vx, vy = velocity
        speed = np.sqrt(vx**2 + vy**2)
        if speed < 0.5:
            return  # Stationary or negligible drift

        cx, cy = center
        target_x = int(cx + vx * scale)
        target_y = int(cy + vy * scale)

        cv2.arrowedLine(
            frame,
            (cx, cy),
            (target_x, target_y),
            color,
            1,
            tipLength=0.35
        )

    def _draw_hud_banner(
        self,
        frame: np.ndarray,
        timestamp: float,
        inference_time_ms: float,
        target_count: int,
        fps: float
    ) -> None:
        """Draws top HUD telemetry banner across the frame."""
        h, w = frame.shape[:2]
        banner_h = 36

        # Translucent top bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (15, 18, 22), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Accent line under banner
        cv2.line(frame, (0, banner_h), (w, banner_h), (0, 255, 200), 1)

        # Telemetry text elements
        system_text = "AI FEED :: MULTI-TARGET TRACKING"
        fps_text = f"FPS: {fps:.1f}"
        latency_text = f"LATENCY: {inference_time_ms:.1f}ms"
        targets_text = f"ACTIVE TRACKS: {target_count}"
        time_text = f"T: {timestamp:05.2f}s"

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.42
        color = (230, 240, 245)

        cv2.putText(frame, system_text, (12, 22), font, scale, (0, 255, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, fps_text, (280, 22), font, scale, color, 1, cv2.LINE_AA)
        cv2.putText(frame, latency_text, (380, 22), font, scale, color, 1, cv2.LINE_AA)
        cv2.putText(frame, targets_text, (520, 22), font, scale, (0, 220, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, time_text, (w - 100, 22), font, scale, color, 1, cv2.LINE_AA)

    def render(
        self,
        frame: np.ndarray,
        result: DetectionFrameResult,
        fps: float = 0.0,
        active_tracks: Optional[List[Any]] = None
    ) -> np.ndarray:
        """
        Renders HUD overlays, bounding boxes, labels, trajectory trails, and telemetry.
        If active_tracks (STrack objects) are provided, uses persistent tracking data.
        """
        annotated = frame.copy()

        # If active tracks are provided from ByteTracker
        if active_tracks is not None:
            for track in active_tracks:
                x1, y1, x2, y2 = track.to_tlbr()
                color = self.colors.get(track.class_name.lower(), self.colors["default"])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                # 1. Motion Trajectory Trail
                if self.render_trajectory and hasattr(track, "trajectory"):
                    self._draw_trajectory(annotated, track.trajectory, color)

                # 2. Velocity Heading Arrow
                if self.render_velocity_vector and hasattr(track, "velocity"):
                    self._draw_velocity_vector(annotated, (cx, cy), track.velocity, color)

                # 3. Subtle bounding box border & Corner brackets
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)
                self._draw_corner_brackets(annotated, (x1, y1, x2, y2), color, line_len=12, thickness=2)

                # 4. Target center crosshair
                self._draw_crosshair(annotated, (cx, cy), color, radius=5)

                # 5. Persistent ID badge: e.g. "DRONE ID 01 [94%]"
                id_str = f"ID {track.track_id:02d}"
                label = f"{track.class_name.upper()} {id_str} {int(track.score * 100)}%"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.4
                thickness = 1
                (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, thickness)

                badge_y1 = max(0, y1 - text_h - 8)
                badge_y2 = y1
                badge_x1 = x1
                badge_x2 = min(annotated.shape[1], x1 + text_w + 10)

                badge_overlay = annotated.copy()
                cv2.rectangle(badge_overlay, (badge_x1, badge_y1), (badge_x2, badge_y2), (20, 20, 25), -1)
                cv2.addWeighted(badge_overlay, 0.8, annotated, 0.2, 0, annotated)

                cv2.rectangle(annotated, (badge_x1, badge_y1), (badge_x2, badge_y2), color, 1)
                cv2.putText(
                    annotated,
                    label,
                    (badge_x1 + 5, badge_y2 - 4),
                    font,
                    font_scale,
                    (255, 255, 255),
                    thickness,
                    cv2.LINE_AA
                )

            target_count = len(active_tracks)
        else:
            # Fallback to plain detections
            for det in result.detections:
                x1, y1, x2, y2 = det.bbox
                color = self.colors.get(det.class_name.lower(), self.colors["default"])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)
                self._draw_corner_brackets(annotated, (x1, y1, x2, y2), color, line_len=12, thickness=2)
                self._draw_crosshair(annotated, (cx, cy), color, radius=5)

                id_part = f" ID {det.object_id:02d}" if det.object_id else ""
                label = f"{det.class_name.upper()}{id_part} {int(det.confidence * 100)}%"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.4
                thickness = 1
                (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, thickness)

                badge_y1 = max(0, y1 - text_h - 8)
                badge_y2 = y1
                badge_x1 = x1
                badge_x2 = min(annotated.shape[1], x1 + text_w + 10)

                badge_overlay = annotated.copy()
                cv2.rectangle(badge_overlay, (badge_x1, badge_y1), (badge_x2, badge_y2), (20, 20, 25), -1)
                cv2.addWeighted(badge_overlay, 0.8, annotated, 0.2, 0, annotated)

                cv2.rectangle(annotated, (badge_x1, badge_y1), (badge_x2, badge_y2), color, 1)
                cv2.putText(
                    annotated,
                    label,
                    (badge_x1 + 5, badge_y2 - 4),
                    font,
                    font_scale,
                    (255, 255, 255),
                    thickness,
                    cv2.LINE_AA
                )
            target_count = len(result.detections)

        # Render top HUD banner if enabled
        if self.hud_enabled:
            self._draw_hud_banner(
                annotated,
                timestamp=result.timestamp,
                inference_time_ms=result.inference_time_ms,
                target_count=target_count,
                fps=fps
            )

        return annotated

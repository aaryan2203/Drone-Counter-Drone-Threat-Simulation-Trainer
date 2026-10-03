"""
Frame Preprocessor Module for AI Detection Pipeline.
Handles frame validation, dimension normalization, aspect-ratio letterboxing,
and illumination enhancement for low-light / degraded conditions.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import cv2
import numpy as np


@dataclass
class PreprocessingMeta:
    """Metadata to map coordinates back to the original frame."""
    original_height: int
    original_width: int
    target_height: int
    target_width: int
    scale_factor: float
    pad_top: int
    pad_left: int


class FramePreprocessor:
    """Preprocesses input video frames for YOLO inference."""

    def __init__(
        self,
        target_width: int = 640,
        target_height: int = 640,
        apply_clahe: bool = False,
        preserve_aspect_ratio: bool = True
    ) -> None:
        self.target_width = target_width
        self.target_height = target_height
        self.apply_clahe = apply_clahe
        self.preserve_aspect_ratio = preserve_aspect_ratio

        # CLAHE (Contrast Limited Adaptive Histogram Equalization) for night/low-light
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def validate_frame(self, frame: Optional[np.ndarray]) -> bool:
        """Validates that the frame is a valid non-empty 3-channel image."""
        if frame is None:
            return False
        if not isinstance(frame, np.ndarray):
            return False
        if frame.size == 0:
            return False
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            return False
        return True

    def enhance_contrast(self, frame: np.ndarray) -> np.ndarray:
        """Enhances contrast in the luminance channel (LAB color space) for low-light conditions."""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        enhanced_l = self._clahe.apply(l_channel)
        merged_lab = cv2.merge((enhanced_l, a_channel, b_channel))
        return cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

    def letterbox(
        self,
        frame: np.ndarray
    ) -> Tuple[np.ndarray, PreprocessingMeta]:
        """Resizes frame with letterboxing (padding) to preserve original aspect ratio."""
        orig_h, orig_w = frame.shape[:2]

        scale = min(self.target_width / orig_w, self.target_height / orig_h)
        new_w = int(round(orig_w * scale))
        new_h = int(round(orig_h * scale))

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        pad_left = (self.target_width - new_w) // 2
        pad_top = (self.target_height - new_h) // 2
        pad_right = self.target_width - new_w - pad_left
        pad_bottom = self.target_height - new_h - pad_top

        # Pad with neutral dark border (114, 114, 114) typical for YOLO
        padded = cv2.copyMakeBorder(
            resized,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114)
        )

        meta = PreprocessingMeta(
            original_height=orig_h,
            original_width=orig_w,
            target_height=self.target_height,
            target_width=self.target_width,
            scale_factor=scale,
            pad_top=pad_top,
            pad_left=pad_left
        )
        return padded, meta

    def preprocess(
        self,
        frame: np.ndarray
    ) -> Tuple[np.ndarray, PreprocessingMeta]:
        """Validates, optionally enhances, and scales the frame."""
        if not self.validate_frame(frame):
            raise ValueError("Input frame is invalid, empty, or not a 3-channel image.")

        working_frame = frame
        if self.apply_clahe:
            working_frame = self.enhance_contrast(working_frame)

        if self.preserve_aspect_ratio:
            return self.letterbox(working_frame)

        orig_h, orig_w = frame.shape[:2]
        resized = cv2.resize(
            working_frame,
            (self.target_width, self.target_height),
            interpolation=cv2.INTER_LINEAR
        )
        meta = PreprocessingMeta(
            original_height=orig_h,
            original_width=orig_w,
            target_height=self.target_height,
            target_width=self.target_width,
            scale_factor=1.0,
            pad_top=0,
            pad_left=0
        )
        return resized, meta

    @staticmethod
    def map_box_to_original(
        bbox: Tuple[float, float, float, float],
        meta: PreprocessingMeta
    ) -> Tuple[int, int, int, int]:
        """Maps bounding box coordinates from letterboxed frame back to original frame."""
        x1, y1, x2, y2 = bbox

        x1_unpad = (x1 - meta.pad_left) / meta.scale_factor
        y1_unpad = (y1 - meta.pad_top) / meta.scale_factor
        x2_unpad = (x2 - meta.pad_left) / meta.scale_factor
        y2_unpad = (y2 - meta.pad_top) / meta.scale_factor

        orig_x1 = max(0, min(int(round(x1_unpad)), meta.original_width))
        orig_y1 = max(0, min(int(round(y1_unpad)), meta.original_height))
        orig_x2 = max(0, min(int(round(x2_unpad)), meta.original_width))
        orig_y2 = max(0, min(int(round(y2_unpad)), meta.original_height))

        return orig_x1, orig_y1, orig_x2, orig_y2

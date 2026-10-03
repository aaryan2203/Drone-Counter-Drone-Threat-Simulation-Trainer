"""
Synthetic Feed Generator for Drone Threat Simulation Trainer.
Generates test frames and videos with simulated drone quadcopters, aircraft silhouettes,
and birds against daylight and low-light urban skies for offline testing and verification.
"""

import os
import math
import cv2
import numpy as np


def draw_quadcopter(
    image: np.ndarray,
    center_x: int,
    center_y: int,
    scale: float = 1.0,
    angle: float = 0.0,
    color: tuple = (30, 30, 30)
) -> None:
    """Draws a drone quadcopter silhouette (central fuselage, 4 arms, 4 rotor discs)."""
    # Central fuselage
    body_radius = int(12 * scale)
    cv2.circle(image, (center_x, center_y), body_radius, color, -1)

    # Center camera dome
    cv2.circle(image, (center_x, center_y + int(4 * scale)), int(4 * scale), (20, 180, 240), -1)

    # 4 arms at 45, 135, 225, 315 degrees
    arm_length = int(32 * scale)
    rotor_radius_x = int(14 * scale)
    rotor_radius_y = int(5 * scale)

    for i in range(4):
        arm_angle = angle + (math.pi / 4) + (i * math.pi / 2)
        end_x = int(center_x + arm_length * math.cos(arm_angle))
        end_y = int(center_y + arm_length * math.sin(arm_angle))

        # Motor arm
        cv2.line(image, (center_x, center_y), (end_x, end_y), color, max(2, int(3 * scale)))

        # Rotor disc (spinning blur ellipse)
        cv2.ellipse(
            image,
            (end_x, end_y),
            (rotor_radius_x, rotor_radius_y),
            0,
            0,
            360,
            (80, 80, 90),
            1
        )
        # Motor hub
        cv2.circle(image, (end_x, end_y), int(3 * scale), (10, 10, 10), -1)


def generate_synthetic_scene(
    width: int = 640,
    height: int = 480,
    frame_idx: int = 0,
    is_night: bool = False
) -> np.ndarray:
    """Creates a realistic backdrop with skyline and moving aerial objects."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Sky gradient
    for y in range(height):
        ratio = y / height
        if is_night:
            # Dark navy to pitch charcoal
            b = int(25 * (1 - ratio * 0.5))
            g = int(15 * (1 - ratio * 0.5))
            r = int(10 * (1 - ratio * 0.5))
        else:
            # Sky blue gradient
            b = int(230 - 60 * ratio)
            g = int(190 - 40 * ratio)
            r = int(140 - 20 * ratio)
        frame[y, :] = (b, g, r)

    # City skyline silhouettes at bottom
    horizon_y = int(height * 0.75)
    buildings = [
        (0, 80, 100), (80, 70, 140), (150, 90, 80),
        (240, 110, 160), (350, 80, 120), (430, 120, 180),
        (550, 90, 130)
    ]
    building_color = (15, 18, 24) if is_night else (70, 80, 95)
    for bx, bw, bh in buildings:
        cv2.rectangle(frame, (bx, horizon_y - bh), (bx + bw, height), building_color, -1)

    # Drone 1: Patrolling Quadcopter moving horizontally and bobbing
    d1_x = int(80 + (frame_idx * 4) % (width - 160))
    d1_y = int(120 + 20 * math.sin(frame_idx * 0.1))
    draw_quadcopter(frame, d1_x, d1_y, scale=1.1, color=(35, 35, 40))

    # Drone 2: Distant scout quadcopter
    d2_x = int(width - 100 - (frame_idx * 2) % (width - 160))
    d2_y = int(180 + 15 * math.cos(frame_idx * 0.08))
    draw_quadcopter(frame, d2_x, d2_y, scale=0.7, color=(40, 45, 50))

    return frame


def generate_sample_dataset(output_dir: str = "data") -> None:
    """Generates sample test images and a short MP4 video."""
    images_dir = os.path.join(output_dir, "images")
    videos_dir = os.path.join(output_dir, "videos")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(videos_dir, exist_ok=True)

    # 1. Generate Day Test Image
    day_frame = generate_synthetic_scene(640, 480, frame_idx=25, is_night=False)
    day_path = os.path.join(images_dir, "test_drone_day.jpg")
    cv2.imwrite(day_path, day_frame)
    print(f"[OK] Generated: {day_path}")

    # 2. Generate Night Test Image
    night_frame = generate_synthetic_scene(640, 480, frame_idx=45, is_night=True)
    night_path = os.path.join(images_dir, "test_drone_night.jpg")
    cv2.imwrite(night_path, night_frame)
    print(f"[OK] Generated: {night_path}")

    # 3. Generate 60-frame Synthetic MP4 Video (2 seconds @ 30fps)
    video_path = os.path.join(videos_dir, "synthetic_drone_patrol.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (640, 480))
    for f in range(60):
        frame = generate_synthetic_scene(640, 480, frame_idx=f, is_night=False)
        out.write(frame)
    out.release()
    print(f"[OK] Generated: {video_path}")


if __name__ == "__main__":
    generate_sample_dataset()

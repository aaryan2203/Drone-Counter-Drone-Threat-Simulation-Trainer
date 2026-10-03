"""
Main Execution Script for Phase 1: AI Detection Pipeline.
Accepts video files, webcams, or images, processes them through the detection pipeline,
renders tactical HUD telemetry, and outputs structured detection events.
"""

import os
import sys
import argparse
import json
import cv2

# Add ai-engine root to Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from inference.pipeline import InferencePipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Drone & Aerial Object Detection Runner")
    parser.add_argument(
        "--source",
        type=str,
        default="data/videos/synthetic_drone_patrol.mp4",
        help="Path to video file, image file, or webcam device index (e.g. '0')"
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="ai-engine/models/yolov8n.pt",
        help="Path to YOLO weights (.pt or .onnx)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/detection_config.json",
        help="Path to JSON configuration file"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.20,
        help="Confidence threshold (0.0 to 1.0)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Inference device: 'cpu' or 'cuda'"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/videos/annotated_output.mp4",
        help="Path to save annotated output video (optional)"
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default="data/detection_events.json",
        help="Path to save structured detection events (JSON)"
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Max frames to process before stopping"
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Display live GUI window during processing (requires display)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("==========================================================")
    print("   AI DRONE THREAT SIMULATION TRAINER - PHASE 1: DETECTION")
    print("==========================================================")
    print(f"Source:     {args.source}")
    print(f"Weights:    {args.weights}")
    print(f"Device:     {args.device}")
    print(f"Confidence: {args.conf}")
    print("==========================================================")

    # Initialize Pipeline
    pipeline = InferencePipeline(
        config_path=args.config,
        weights_path=args.weights,
        confidence_threshold=args.conf,
        device=args.device
    )

    # Check if source is a single image
    if os.path.isfile(args.source) and args.source.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
        frame = cv2.imread(args.source)
        if frame is None:
            print(f"[ERROR] Could not read image: {args.source}")
            sys.exit(1)

        annotated, result, events = pipeline.process_frame(frame, timestamp=0.0, fps=30.0)
        print(f"\n[RESULTS] Detected {len(result.detections)} objects in {result.inference_time_ms:.1f}ms:")
        for det in result.detections:
            print(f"  - Class: {det.class_name:<10} Conf: {det.confidence:.2f} BBox: {det.bbox}")

        # Save annotated image
        out_img_path = os.path.splitext(args.source)[0] + "_detected.jpg"
        cv2.imwrite(out_img_path, annotated)
        print(f"\n[OK] Annotated image saved to: {out_img_path}")

        # Save JSON events
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump([d.to_dict() for d in [result]], f, indent=2)
        print(f"[OK] Detection events saved to: {args.json_output}")
        return

    # Check if source is camera index
    source_val = int(args.source) if args.source.isdigit() else args.source

    def on_event(frame_events):
        for e in frame_events:
            print(f"[EVENT @ {e['timestamp']:.2f}s] Object {e['object_id']} ({e['class']}) detected with {e['confidence']*100:.1f}% confidence at {e['bbox']}")

    print("\nStarting video inference stream...")
    events = pipeline.process_video(
        video_source=source_val,
        output_video_path=args.output,
        event_callback=on_event,
        max_frames=args.max_frames,
        display=args.display
    )

    print("\n==========================================================")
    print(f"Processing Complete! Total Events Emitted: {len(events)}")
    if args.output:
        print(f"Annotated Video: {args.output}")

    # Save events to JSON
    with open(args.json_output, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    print(f"Event Log Saved: {args.json_output}")
    print("==========================================================")


if __name__ == "__main__":
    main()

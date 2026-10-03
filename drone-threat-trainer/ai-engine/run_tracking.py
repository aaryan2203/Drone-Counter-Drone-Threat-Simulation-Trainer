"""
Main Execution Script for Phase 2: AI Multi-Object Tracking Pipeline.
Processes video streams, assigns and maintains persistent object IDs,
renders trajectory trails and velocity vectors, and logs structured tracking events.
"""

import os
import sys
import argparse
import json

# Add ai-engine root to Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from inference.pipeline import InferencePipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Drone & Aerial Object Tracking Runner")
    parser.add_argument(
        "--source",
        type=str,
        default="data/videos/synthetic_drone_patrol.mp4",
        help="Path to video file or webcam device index (e.g. '0')"
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
        help="Path to detection configuration JSON"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.15,
        help="Detection confidence threshold (0.0 to 1.0)"
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
        default="data/videos/tracked_output.mp4",
        help="Path to save annotated output video"
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default="data/tracking_events.json",
        help="Path to save structured tracking events (JSON)"
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default="SES_001",
        help="Training session identifier"
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
    print("   AI DRONE THREAT SIMULATION TRAINER - PHASE 2: TRACKING")
    print("==========================================================")
    print(f"Session ID:  {args.session_id}")
    print(f"Source:      {args.source}")
    print(f"Weights:     {args.weights}")
    print(f"Confidence:  {args.conf}")
    print(f"Device:      {args.device}")
    print("==========================================================")

    # Initialize Pipeline with ByteTracker enabled
    pipeline = InferencePipeline(
        config_path=args.config,
        weights_path=args.weights,
        confidence_threshold=args.conf,
        device=args.device,
        enable_tracking=True
    )
    pipeline.reset_tracker(session_id=args.session_id)

    source_val = int(args.source) if args.source.isdigit() else args.source

    def on_event(frame_events):
        for e in frame_events:
            v = e.get("velocity", [0.0, 0.0])
            print(
                f"[{e['timestamp']:05.2f}s | {e['session_id']}] "
                f"TRACK ID {e['object_id']:02d} ({e['class']}) "
                f"Conf: {e['confidence']*100:4.1f}% | "
                f"BBox: {e['bbox']} | "
                f"Vel: ({v[0]:+5.1f}, {v[1]:+5.1f}) px/f"
            )

    print("\nStarting video tracking stream...\n")
    events = pipeline.process_video(
        video_source=source_val,
        output_video_path=args.output,
        event_callback=on_event,
        max_frames=args.max_frames,
        display=args.display
    )

    print("\n==========================================================")
    print(f"Tracking Complete! Total Events Emitted: {len(events)}")
    if args.output:
        print(f"Tracked Video:  {args.output}")

    # Save events to JSON
    with open(args.json_output, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    print(f"Tracking Events: {args.json_output}")
    print("==========================================================")


if __name__ == "__main__":
    main()

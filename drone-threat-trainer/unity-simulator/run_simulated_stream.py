"""
Simulation Stream Runner & Unity-AI Communication Bridge.
Simulates a real-time 3D aerial camera perspective stream, connects to the FastAPI backend,
runs the AI perception & ByteTrack pipeline on simulated camera frames, broadcasts live
telemetry over WebSocket, and submits simulated trainee interaction decisions.
"""

import os
import sys
import time
import math
import json
import argparse
import asyncio
import numpy as np
import cv2
import httpx
import websockets

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
AI_ENGINE_ROOT = os.path.join(PROJECT_ROOT, "ai-engine")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if AI_ENGINE_ROOT not in sys.path:
    sys.path.insert(0, AI_ENGINE_ROOT)

from inference.pipeline import InferencePipeline
from data.generate_synthetic_feed import generate_synthetic_scene


async def run_simulation_bridge(
    api_url: str = "http://127.0.0.1:8000/api",
    ws_url: str = "ws://127.0.0.1:8000/ws/telemetry",
    trainee_code: str = "TRN-042",
    difficulty: str = "medium",
    duration_frames: int = 40,
    display: bool = False
):
    print("==========================================================")
    print("   AI DRONE THREAT SIMULATOR - UNITY-AI RUNTIME BRIDGE")
    print("==========================================================")
    print(f"Backend API:   {api_url}")
    print(f"WebSocket:     {ws_url}")
    print(f"Trainee Code:  {trainee_code}")
    print(f"Difficulty:    {difficulty}")
    print("==========================================================")

    # Step 1: Start Session via REST
    async with httpx.AsyncClient() as client:
        start_payload = {
            "trainee_code": trainee_code,
            "difficulty": difficulty
        }
        print(f"\n[1/5] Initiating session on FastAPI backend...")
        try:
            start_resp = await client.post(f"{api_url}/sessions/start", json=start_payload, timeout=5.0)
            if start_resp.status_code != 201:
                print(f"[ERROR] Failed to start session: {start_resp.text}")
                return
            session_data = start_resp.json()
            session_code = session_data["session_code"]
            print(f"[OK] Session Started: {session_code} (Scenario: {session_data['scenario_code']})")
        except Exception as e:
            print(f"[ERROR] Could not connect to FastAPI server at {api_url}: {e}")
            print("Please ensure the FastAPI backend is running via: python backend/run_server.py")
            return

    # Step 2: Initialize AI Detection & Tracking Pipeline
    weights_path = os.path.join(AI_ENGINE_ROOT, "models", "yolov8n.pt")
    pipeline = InferencePipeline(
        weights_path=weights_path,
        confidence_threshold=0.15,
        enable_tracking=True
    )
    pipeline.reset_tracker(session_id=session_code)

    # Step 3: Connect to WebSocket Telemetry Hub
    print(f"\n[2/5] Connecting to Telemetry WebSocket: {ws_url}...")
    try:
        async with websockets.connect(ws_url) as ws:
            # Receive initial handshake
            handshake = await ws.recv()
            print(f"[OK] WebSocket Handshake received: {handshake}")

            print(f"\n[3/5] Streaming simulated 3D camera frames through AI Pipeline...")
            sim_fps = 15.0
            total_detections_logged = 0

            for frame_idx in range(duration_frames):
                sim_timestamp = round(frame_idx / sim_fps, 2)

                # Generate simulated camera frame (Day/Night depending on difficulty)
                is_night = (difficulty in ["hard", "expert"])
                frame = generate_synthetic_scene(640, 480, frame_idx=frame_idx, is_night=is_night)

                # Process frame through YOLO + ByteTracker + Tactical HUD
                annotated, result, events = pipeline.process_frame(
                    frame=frame,
                    timestamp=sim_timestamp,
                    fps=sim_fps
                )

                # Broadcast live telemetry over WebSocket
                for ev in events:
                    total_detections_logged += 1
                    # Send detection event to WebSocket
                    await ws.send(json.dumps(ev))

                    # Send to REST API (asynchronous post)
                    async with httpx.AsyncClient() as client:
                        api_event = {
                            "session_code": session_code,
                            "timestamp": ev["timestamp"],
                            "object_id": ev["object_id"],
                            "class": ev["class"],
                            "confidence": ev["confidence"],
                            "bbox": ev["bbox"]
                        }
                        await client.post(f"{api_url}/events", json=api_event)

                # Simulate trainee interaction at intervals
                if frame_idx == 10 and events:
                    target_id = events[0]["object_id"]
                    print(f"\n >>> [TRAINEE ACTION] Trainee spotted target ID {target_id:02d} -> [DETECT]")
                    async with httpx.AsyncClient() as client:
                        action_data = {
                            "session_code": session_code,
                            "object_id": target_id,
                            "action": "detect",
                            "timestamp": sim_timestamp,
                            "correct": True,
                            "response_time": 2.15
                        }
                        await client.post(f"{api_url}/actions", json=action_data)

                if frame_idx == 20 and events:
                    target_id = events[0]["object_id"]
                    print(f" >>> [TRAINEE ACTION] Trainee classified target ID {target_id:02d} -> [IDENTIFY: DRONE]")
                    async with httpx.AsyncClient() as client:
                        action_data = {
                            "session_code": session_code,
                            "object_id": target_id,
                            "action": "identify_drone",
                            "timestamp": sim_timestamp,
                            "correct": True,
                            "response_time": 3.40
                        }
                        await client.post(f"{api_url}/actions", json=action_data)

                if frame_idx == 30 and events:
                    target_id = events[0]["object_id"]
                    print(f" >>> [TRAINEE ACTION] Trainee submitted response on ID {target_id:02d} -> [RESPOND: RF_JAMMING]")
                    async with httpx.AsyncClient() as client:
                        action_data = {
                            "session_code": session_code,
                            "object_id": target_id,
                            "action": "respond_jam_rf",
                            "timestamp": sim_timestamp,
                            "correct": True,
                            "response_time": 4.10
                        }
                        await client.post(f"{api_url}/actions", json=action_data)

                if display:
                    try:
                        cv2.imshow("Simulation Camera Feed", annotated)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    except Exception:
                        pass

                await asyncio.sleep(0.04)  # ~25 FPS pacing

            if display:
                try:
                    cv2.destroyAllWindows()
                except Exception:
                    pass

            print(f"\n[4/5] Concluding training session and generating AAR Report...")
            async with httpx.AsyncClient() as client:
                end_resp = await client.post(f"{api_url}/sessions/end", json={"session_code": session_code})
                aar_data = end_resp.json()

            print("\n==========================================================")
            print("                AFTER-ACTION REVIEW (AAR)")
            print("==========================================================")
            print(f"Session Code:         {aar_data['session_code']}")
            print(f"Trainee:              {aar_data['trainee_code']}")
            print(f"Scenario:             {aar_data['scenario_code']} ({aar_data['environment']} / {aar_data['lighting']})")
            print(f"Difficulty:           {aar_data['difficulty'].upper()}")
            print(f"Detection Score:      {aar_data['detection_score']}%")
            print(f"Classification Score: {aar_data['classification_score']}%")
            print(f"Decision Score:       {aar_data['decision_score']}%")
            print(f"Avg Response Time:    {aar_data['avg_response_time']}s")
            print("----------------------------------------------------------")
            print(f"OVERALL SCORE:        {aar_data['overall_score']}%")
            print("==========================================================")
            print("[5/5] End-to-End Simulation & Verification Succeeded!\n")

    except Exception as ex:
        print(f"[ERROR] Simulation loop error: {ex}")


def main():
    parser = argparse.ArgumentParser(description="Unity-AI Simulation Stream Runner")
    parser.add_argument("--api", type=str, default="http://127.0.0.1:8000/api")
    parser.add_argument("--ws", type=str, default="ws://127.0.0.1:8000/ws/telemetry")
    parser.add_argument("--trainee", type=str, default="TRN-042")
    parser.add_argument("--difficulty", type=str, default="medium")
    parser.add_argument("--frames", type=int, default=35)
    parser.add_argument("--display", action="store_true")
    args = parser.parse_args()

    asyncio.run(run_simulation_bridge(
        api_url=args.api,
        ws_url=args.ws,
        trainee_code=args.trainee,
        difficulty=args.difficulty,
        duration_frames=args.frames,
        display=args.display
    ))


if __name__ == "__main__":
    main()

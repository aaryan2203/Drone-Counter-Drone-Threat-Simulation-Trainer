# AI-Enabled Drone & Counter-Drone Threat Simulation Trainer

**Problem Statement ID:** 26247  
**System Type:** Modular, offline-capable simulation, perception, decision evaluation, and after-action review (AAR) trainer.  
**Safety Notice:** This system is strictly a training simulator. It does NOT implement real-world weapon control, weapon firing, attack guidance, or autonomous engagement.

---

## 1. Project Overview

The **AI-Enabled Drone & Counter-Drone Threat Simulation Trainer** is an offline-first modular software platform built to train security and defense personnel in identifying, tracking, evaluating, and responding to simulated airborne drone threats.

The platform supports two primary operating modes:
* **Mode A — Camera / Video**: USB Cameras, live feeds, or recorded MP4/AVI footage processed through computer vision and tracking.
* **Mode B — Simulation**: Configurable procedural 3D environments (Unity / Python Bridge) streaming synthetic camera frames and target telemetry.

Both modes share the identical AI perception engine, event logging schemas, decision evaluation rules, and After-Action Review (AAR) analytics.

---

## 2. High-Level Architecture

```text
                         ┌──────────────────┐
                         │     TRAINEE      │
                         └────────┬─────────┘
                                  │
                                  ▼
                       ┌────────────────────┐
                       │   UNITY SIMULATOR  │
                       │                    │
                       │ Environment        │
                       │ Scenario           │
                       │ Simulated Objects  │
                       │ Trainee Interface  │
                       └─────────┬──────────┘
                                 │
                         Video / Events
                                 │
                                 ▼
                       ┌────────────────────┐
                       │      FASTAPI       │
                       │    BACKEND API     │
                       └─────────┬──────────┘
                                 │
                                 ▼
                       ┌────────────────────┐
                       │     PYTHON AI      │
                       │                    │
                       │ OpenCV / YOLO      │
                       │ ByteTrack Tracking │
                       │ Kalman Filter      │
                       └─────────┬──────────┘
                                 │
                                 ▼
                       ┌────────────────────┐
                       │ SIMULATION RULES   │
                       │ & THREAT STATE     │
                       └─────────┬──────────┘
                                 │
                                 ▼
                       ┌────────────────────┐
                       │   SCORING ENGINE   │
                       └─────────┬──────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
             ┌──────────────┐         ┌───────────────┐
             │    SQLite    │         │ AAR Dashboard │
             │   Database   │         │ Next.js/React │
             └──────────────┘         └───────────────┘
```

---

## 3. Technology Stack

* **AI / Perception**: Python, PyTorch, YOLOv8, OpenCV, NumPy, ByteTrack (with Kalman Filter state estimation).
* **Backend API**: FastAPI, Pydantic v2, SQLAlchemy, WebSockets, Uvicorn.
* **Database**: SQLite (local, offline-first) with SQLAlchemy ORM.
* **Simulation**: Unity 2022.3 LTS (C#), Unity XR Toolkit ready, plus zero-dependency Python 3D simulation bridge.
* **Dashboard**: Next.js 16, TypeScript, Tailwind CSS, shadcn/ui components, HTML5 Radar Canvas, and Chart.js.
* **Deployment**: 100% offline-capable, local inference, no cloud API prerequisites.

---

## 4. Directory Structure

```text
drone-threat-trainer/
├── ai-engine/                       # Perception & Tracking
│   ├── detection/
│   │   ├── yolo_detector.py         # YOLO inference and box mapping
│   │   └── visualizer.py            # Futuristic tactical military HUD
│   ├── tracking/
│   │   ├── kalman_filter.py         # 8-state constant velocity motion filter
│   │   └── byte_tracker.py          # Persistent multi-target ByteTrack tracker
│   ├── preprocessing/
│   │   └── frame_preprocessor.py    # Letterboxing, validation, CLAHE contrast
│   ├── inference/
│   │   └── pipeline.py              # End-to-end unified input pipeline
│   ├── models/                      # Local weights (yolov8n.pt)
│   ├── tests/                       # Detection and tracking tests
│   ├── run_detection.py             # Detection CLI runner
│   └── run_tracking.py              # Tracking CLI runner
│
├── backend/                         # FastAPI Application
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints.py         # REST routes (Sessions, AAR, Events)
│   │   │   └── websocket.py         # Telemetry WebSocket hub
│   │   ├── database/
│   │   │   ├── models.py            # SQLAlchemy 6 tables
│   │   │   └── session.py           # SQLite connection pool
│   │   ├── schemas/
│   │   │   └── schemas.py           # Pydantic data contracts
│   │   ├── services/
│   │   │   ├── scenario_service.py  # Procedural scenario generator
│   │   │   └── session_service.py   # State and scoring engine
│   │   └── main.py                  # App entrypoint and static mount
│   ├── tests/
│   │   └── test_backend.py          # Integration test suite
│   └── run_server.py                # Server launcher script
│
├── unity-simulator/                 # Unity 3D C# Simulation
│   ├── Assets/Scripts/
│   │   ├── NetworkClient.cs         # REST + WebSocket client
│   │   ├── DroneController.cs       # Quadcopter dynamics & waypoints
│   │   ├── DroneSpawner.cs          # Procedural target spawner
│   │   ├── SimulationEnvironmentManager.cs # Lighting & fog
│   │   ├── SimulationCameraCapture.cs      # Frame capture & streaming
│   │   └── TraineeInterfaceController.cs   # Trainee action controls
│   ├── tests/
│   │   └── test_simulation_integration.py # Unity-AI integration tests
│   └── run_simulated_stream.py      # Standalone simulation bridge
│
├── dashboard/                       # Trainee Console & AAR Analytics
│   ├── src/                         # Next.js 16 + React 19 + shadcn/ui
│   │   ├── components/
│   │   │   ├── RadarView.tsx        # 360° interactive radar canvas
│   │   │   ├── TraineeControls.tsx  # [DETECT], [IDENTIFY], [TRACK], [RESPOND]
│   │   │   ├── AARReportView.tsx    # After-action report gauges & timeline
│   │   │   └── PerformanceHistoryChart.tsx # Historical trend charts
│   │   └── app/page.tsx             # Interactive console
│   └── public/index.html            # Standalone zero-install dashboard
│
├── configs/                         # Configurable JSON thresholds
│   ├── detection_config.json
│   └── tracking_config.json
├── data/                            # Synthetic test data & logs
└── requirements.txt                 # Pinned Python dependencies
```

---

## 5. Installation & Setup

### Prerequisites
* Python 3.10+ (Tested on Python 3.14 on Windows)
* Node.js v18+ (Optional, for building Next.js dashboard; standalone HTML dashboard runs with zero install)

### 1. Install Python Dependencies
```powershell
cd C:\Users\Nikhil\.gemini\antigravity\scratch\drone-threat-trainer
pip install -r requirements.txt
```

### 2. Generate Offline Test Feed
```powershell
python data/generate_synthetic_feed.py
```

---

## 6. Execution Guide

### 1. Launch FastAPI Backend & Dashboard
```powershell
python backend/run_server.py
```
* **Interactive Web Dashboard**: `http://127.0.0.1:8000/dashboard` (or `http://127.0.0.1:8000/`)
* **API Documentation (Swagger UI)**: `http://127.0.0.1:8000/docs`
* **WebSocket Telemetry Stream**: `ws://127.0.0.1:8000/ws/telemetry`

### 2. Run Autonomous Simulation Stream
In a separate terminal, launch the simulation bridge to run an automated training session with live radar streaming, target classification, and AAR generation:
```powershell
python unity-simulator/run_simulated_stream.py `
  --trainee "CADET-01" `
  --difficulty "hard" `
  --frames 40
```

### 3. Run AI Tracking on Video or Webcam
```powershell
# Video file
python ai-engine/run_tracking.py `
  --source data/videos/synthetic_drone_patrol.mp4 `
  --weights ai-engine/models/yolov8n.pt `
  --output data/videos/tracked_output.mp4

# Live USB Camera / Webcam
python ai-engine/run_tracking.py --source 0 --display
```

### 4. Run Next.js 16 Dashboard (Development Mode)
```powershell
cd dashboard
npm.cmd install
npm.cmd run dev
```
Navigate to `http://localhost:3000`.

---

## 7. Testing & Verification

Run the complete 24-test test suite covering AI detection, ByteTrack tracking, REST endpoints, WebSockets, and simulation lifecycle:
```powershell
python -m pytest ai-engine/tests/ backend/tests/ unity-simulator/tests/ -v
```

**Verification Results:**
* `ai-engine/tests/test_detection.py`: 8 Passed (Preprocessing, YOLO validation, HUD overlay, event format)
* `ai-engine/tests/test_tracking.py`: 8 Passed (Kalman filter, persistent IDs, occlusion recovery)
* `backend/tests/test_backend.py`: 6 Passed (Endpoints, database operations, WebSockets)
* `unity-simulator/tests/test_simulation_integration.py`: 2 Passed (Simulation frame stream, end-to-end AAR)

---

## 8. Configurable Scoring Formula (Section 12)

Overall score calculation uses configurable weights stored in [`backend/app/services/session_service.py`](file:///C:/Users/Nikhil/.gemini/antigravity/scratch/drone-threat-trainer/backend/app/services/session_service.py):
$$\text{Overall Score} = 0.30 \times \text{Detection} + 0.30 \times \text{Classification} + 0.30 \times \text{Decision} + 0.10 \times \text{Latency}$$

* **Detection Score**: Percentage of spawned targets detected by perception.
* **Classification Score**: Correct identification of target class (Drone vs Bird vs Aircraft).
* **Decision Score**: Appropriateness of selected training protocol (e.g. RF Jamming vs Advisory alert).
* **Latency Score**: Speed of trainee reaction (benchmark: $\le 2.0\text{s} = 100\%$, scaling down to $10.0\text{s} = 0\%$).

---

## 9. Safety and Operational Scope

As mandated by safety directives:
* This software is intended exclusively for **training and skill development**.
* The system evaluates human response latencies and adherence to standard protocols.
* It does NOT interface with physical counter-drone weapons or real-world targeting hardware.

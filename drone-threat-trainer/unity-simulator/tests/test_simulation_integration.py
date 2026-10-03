"""
Integration Tests for Simulation Engine & Unity-AI Communication Bridge.
Verifies camera frame generation, 3D-to-2D projection simulation,
FastAPI REST integration, and trainee decision evaluation.
"""

import os
import sys
import pytest
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SIM_DIR = os.path.dirname(TEST_DIR)
PROJECT_ROOT = os.path.dirname(SIM_DIR)
AI_ENGINE_ROOT = os.path.join(PROJECT_ROOT, "ai-engine")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if AI_ENGINE_ROOT not in sys.path:
    sys.path.insert(0, AI_ENGINE_ROOT)

from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.database.models import Base
from data.generate_synthetic_feed import generate_synthetic_scene
from inference.pipeline import InferencePipeline

# Isolated test DB
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=test_engine)

client = TestClient(app)


def test_simulation_day_and_night_scene_generation():
    """Verify simulation camera frame generation across day and night conditions."""
    day_frame = generate_synthetic_scene(640, 480, frame_idx=0, is_night=False)
    night_frame = generate_synthetic_scene(640, 480, frame_idx=0, is_night=True)

    assert day_frame.shape == (480, 640, 3)
    assert night_frame.shape == (480, 640, 3)

    # Night frame should have lower average luminance than day frame
    assert np.mean(night_frame) < np.mean(day_frame)


def test_simulation_to_ai_and_backend_lifecycle():
    """
    Tests complete integration loop:
    Simulation frame -> AI perception & tracking -> FastAPI session & actions -> AAR report
    """
    # 1. Start simulation session on backend
    start_resp = client.post("/api/sessions/start", json={"trainee_code": "CADET-SIM", "difficulty": "hard"})
    assert start_resp.status_code == 201
    session_data = start_resp.json()
    session_code = session_data["session_code"]

    # 2. Run simulation frame through AI Pipeline
    weights_path = os.path.join(AI_ENGINE_ROOT, "models", "yolov8n.pt")
    if not os.path.exists(weights_path):
        pytest.skip("Model weights not present")

    pipeline = InferencePipeline(weights_path=weights_path, confidence_threshold=0.10, enable_tracking=True)
    pipeline.reset_tracker(session_code)

    sim_frame = generate_synthetic_scene(640, 480, frame_idx=10, is_night=True)
    annotated, result, events = pipeline.process_frame(sim_frame, timestamp=1.2, fps=15.0)

    assert isinstance(annotated, np.ndarray)
    assert isinstance(events, list)

    # 3. Ingest tracking events into backend
    for ev in events:
        post_resp = client.post("/api/events", json={
            "session_code": session_code,
            "timestamp": ev["timestamp"],
            "object_id": ev["object_id"],
            "class": ev["class"],
            "confidence": ev["confidence"],
            "bbox": ev["bbox"]
        })
        assert post_resp.status_code == 201

    # 4. Trainee selects target and executes predefined training actions
    target_id = events[0]["object_id"] if events else 1

    # Action 1: [DETECT]
    client.post("/api/actions", json={
        "session_code": session_code,
        "object_id": target_id,
        "action": "detect",
        "timestamp": 1.5,
        "correct": True,
        "response_time": 1.8
    })

    # Action 2: [IDENTIFY]
    client.post("/api/actions", json={
        "session_code": session_code,
        "object_id": target_id,
        "action": "classify_drone",
        "timestamp": 2.8,
        "correct": True,
        "response_time": 2.5
    })

    # Action 3: [RESPOND]
    client.post("/api/actions", json={
        "session_code": session_code,
        "object_id": target_id,
        "action": "respond_jam_rf",
        "timestamp": 3.6,
        "correct": True,
        "response_time": 3.2
    })

    # 5. Conclude session and verify AAR calculation
    end_resp = client.post("/api/sessions/end", json={"session_code": session_code})
    assert end_resp.status_code == 200
    aar = end_resp.json()

    assert aar["session_code"] == session_code
    assert aar["total_actions"] == 3
    assert aar["correct_actions"] == 3
    assert aar["decision_score"] == 100.0
    assert aar["overall_score"] > 0.0

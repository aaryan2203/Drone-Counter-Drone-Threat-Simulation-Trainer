"""
Integration & End-to-End Tests for FastAPI Backend.
Tests database operations, REST endpoints, procedural scenario generation,
event logging, action evaluation, AAR report generation, and WebSocket telemetry.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TEST_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.database.models import Base

from sqlalchemy.pool import StaticPool

# Setup isolated in-memory SQLite database for testing with StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
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


# =====================================================================
# 1. Health Endpoint Test
# =====================================================================

def test_health_check():
    """Verify health endpoint responds with healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "AI Drone & Counter-Drone Threat Simulation Trainer" in data["system"]


# =====================================================================
# 2. Trainee Registration Tests
# =====================================================================

def test_register_trainee():
    """Verify trainee registration and idempotency."""
    payload = {"trainee_code": "TRN-101", "name": "Lieutenant Ripley"}
    resp = client.post("/api/trainees", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["trainee_code"] == "TRN-101"
    assert data["name"] == "Lieutenant Ripley"

    # Idempotent re-registration returns existing record
    resp2 = client.post("/api/trainees", json=payload)
    assert resp2.status_code == 201
    assert resp2.json()["id"] == data["id"]


# =====================================================================
# 3. Procedural Scenario Generator Tests (Section 9)
# =====================================================================

def test_generate_scenario_random():
    """Verify procedural generation of scenario with difficulty preset."""
    payload = {"difficulty": "hard", "duration": 180}
    resp = client.post("/api/scenarios/generate", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["difficulty"] == "hard"
    assert data["environment"] in ["urban", "industrial"]
    assert data["lighting"] in ["night", "low_light"]
    assert 5 <= data["object_count"] <= 8
    assert data["seed"] > 0
    assert data["scenario_code"].startswith("SCN_")


def test_generate_scenario_deterministic_seed():
    """Verify that using the same random seed produces the exact same scenario parameters."""
    fixed_seed = 424242
    payload = {"difficulty": "medium", "seed": fixed_seed}

    resp1 = client.post("/api/scenarios/generate", json=payload)
    resp2 = client.post("/api/scenarios/generate", json=payload)

    data1 = resp1.json()
    data2 = resp2.json()

    assert data1["environment"] == data2["environment"]
    assert data1["lighting"] == data2["lighting"]
    assert data1["visibility"] == data2["visibility"]
    assert data1["object_count"] == data2["object_count"]


# =====================================================================
# 4. Session, Perception & Action Flow (End-to-End Simulation)
# =====================================================================

def test_full_session_simulation_lifecycle():
    """
    Simulates a full trainee session:
    1. Start session
    2. Ingest AI detection events
    3. Ingest trainee actions (detection, response)
    4. End session and calculate AAR report
    5. Query AAR report & performance history
    """
    # Step 1: Start Session
    start_payload = {
        "trainee_code": "TRN-101",
        "difficulty": "medium"
    }
    start_resp = client.post("/api/sessions/start", json=start_payload)
    assert start_resp.status_code == 201
    session_data = start_resp.json()
    session_code = session_data["session_code"]
    assert session_data["status"] == "in_progress"

    # Step 2: Log AI Detection Events
    det_event = {
        "session_code": session_code,
        "timestamp": 12.42,
        "object_id": 3,
        "class": "drone",
        "confidence": 0.94,
        "bbox": [120, 80, 310, 240]
    }
    det_resp = client.post("/api/events", json=det_event)
    assert det_resp.status_code == 201
    assert det_resp.json()["object_id"] == 3
    assert det_resp.json()["class_name"] == "drone"

    # Step 3: Trainee Decision / Action
    action_event = {
        "session_code": session_code,
        "object_id": 3,
        "action": "respond_jam_rf",
        "timestamp": 14.80,
        "correct": True,
        "response_time": 2.38
    }
    action_resp = client.post("/api/actions", json=action_event)
    assert action_resp.status_code == 201
    assert action_resp.json()["action"] == "respond_jam_rf"

    # Step 4: End Session & Generate AAR
    end_payload = {"session_code": session_code}
    end_resp = client.post("/api/sessions/end", json=end_payload)
    assert end_resp.status_code == 200
    aar_data = end_resp.json()

    assert aar_data["session_code"] == session_code
    assert aar_data["trainee_code"] == "TRN-101"
    assert aar_data["detection_score"] > 0
    assert aar_data["decision_score"] == 100.0  # 1/1 correct action
    assert aar_data["overall_score"] > 0
    assert aar_data["total_detections"] == 1
    assert aar_data["total_actions"] == 1
    assert aar_data["avg_response_time"] == 2.38

    # Step 5: Query AAR Report endpoint
    aar_get_resp = client.get(f"/api/aar/{session_code}")
    assert aar_get_resp.status_code == 200
    assert aar_get_resp.json()["overall_score"] == aar_data["overall_score"]

    # Step 6: Query Performance History
    perf_resp = client.get("/api/performance/TRN-101")
    assert perf_resp.status_code == 200
    perf_data = perf_resp.json()
    assert perf_data["total_sessions"] == 1
    assert perf_data["trainee_code"] == "TRN-101"
    assert len(perf_data["sessions"]) == 1
    assert perf_data["sessions"][0]["session_code"] == session_code


# =====================================================================
# 5. WebSocket Telemetry Test
# =====================================================================

def test_websocket_telemetry():
    """Verify WebSocket handshake and broadcast capability."""
    with client.websocket_connect("/ws/telemetry") as websocket:
        # Expect handshake message
        handshake = websocket.receive_json()
        assert handshake["event"] == "connected"
        assert "active_clients" in handshake

        # Send test message from client
        test_payload = {"event": "sim_ping", "data": "hello_unity"}
        websocket.send_json(test_payload)

        # Receive echo / broadcast
        echo = websocket.receive_json()
        assert echo["event"] == "sim_ping"
        assert echo["data"] == "hello_unity"

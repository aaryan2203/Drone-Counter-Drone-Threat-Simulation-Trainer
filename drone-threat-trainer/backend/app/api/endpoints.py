"""
REST API Endpoints for Drone Threat Simulation Trainer.
Provides complete CRUD and workflow management for trainees, scenarios,
sessions, perception events, trainee actions, and AAR reports.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..database.models import Trainee, Scenario, TrainingSession
from ..schemas.schemas import (
    TraineeCreate, TraineeResponse,
    ScenarioGenerateRequest, ScenarioResponse,
    SessionStartRequest, SessionEndRequest, SessionResponse,
    DetectionEventCreate, DetectionEventResponse,
    TraineeActionCreate, TraineeActionResponse,
    AARReportResponse, PerformanceHistoryResponse
)
from ..services.scenario_service import ScenarioService
from ..services.session_service import SessionService
from .websocket import manager

router = APIRouter(prefix="/api", tags=["Drone Threat Trainer API"])


# =====================================================================
# Health Check
# =====================================================================

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Returns system status and connection information."""
    return {
        "status": "healthy",
        "system": "AI Drone & Counter-Drone Threat Simulation Trainer",
        "active_ws_connections": len(manager.active_connections)
    }


# =====================================================================
# Trainees
# =====================================================================

@router.post("/trainees", response_model=TraineeResponse, status_code=status.HTTP_201_CREATED)
async def register_trainee(req: TraineeCreate, db: Session = Depends(get_db)):
    """Registers a new trainee."""
    existing = db.query(Trainee).filter(Trainee.trainee_code == req.trainee_code).first()
    if existing:
        return existing
    trainee = Trainee(trainee_code=req.trainee_code, name=req.name)
    db.add(trainee)
    db.commit()
    db.refresh(trainee)
    return trainee


# =====================================================================
# Scenarios (Section 9)
# =====================================================================

@router.post("/scenarios/generate", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def generate_scenario(req: ScenarioGenerateRequest, db: Session = Depends(get_db)):
    """Procedurally generates a new randomized or seeded scenario."""
    scenario = ScenarioService.generate_scenario(db, req)
    return scenario


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Retrieves scenario details by ID."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario with ID {scenario_id} not found")
    return scenario


# =====================================================================
# Sessions
# =====================================================================

@router.post("/sessions/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(req: SessionStartRequest, db: Session = Depends(get_db)):
    """Initializes a new training session with a scenario."""
    session = SessionService.start_session(db, req)
    res = SessionResponse(
        id=session.id,
        session_code=session.session_code,
        trainee_code=session.trainee.trainee_code,
        scenario_code=session.scenario.scenario_code,
        status=session.status,
        start_time=session.start_time,
        end_time=session.end_time,
        overall_score=session.overall_score
    )

    # Broadcast session started event to WebSocket subscribers
    await manager.broadcast({
        "event": "session_started",
        "session_code": session.session_code,
        "trainee_code": session.trainee.trainee_code,
        "difficulty": session.scenario.difficulty
    })

    return res


@router.get("/sessions/{session_code}", response_model=SessionResponse)
async def get_session(session_code: str, db: Session = Depends(get_db)):
    """Retrieves session details by session code."""
    session = db.query(TrainingSession).filter(TrainingSession.session_code == session_code).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_code} not found")

    return SessionResponse(
        id=session.id,
        session_code=session.session_code,
        trainee_code=session.trainee.trainee_code,
        scenario_code=session.scenario.scenario_code,
        status=session.status,
        start_time=session.start_time,
        end_time=session.end_time,
        overall_score=session.overall_score
    )


@router.post("/sessions/end", response_model=AARReportResponse)
async def end_session(req: SessionEndRequest, db: Session = Depends(get_db)):
    """Concludes the training session and computes the After-Action Review (AAR) report."""
    SessionService.end_session(db, req.session_code)
    report = SessionService.get_aar_report_response(db, req.session_code)

    # Broadcast session ended event to WebSocket subscribers
    await manager.broadcast({
        "event": "session_completed",
        "session_code": req.session_code,
        "overall_score": report.overall_score
    })

    return report


# =====================================================================
# Events & Actions (Section 13)
# =====================================================================

@router.post("/events", response_model=DetectionEventResponse, status_code=status.HTTP_201_CREATED)
async def record_detection_event(event: DetectionEventCreate, db: Session = Depends(get_db)):
    """Logs an AI perception/detection event from video, camera, or simulation stream."""
    record = SessionService.record_detection(db, event)

    # Broadcast event to WebSocket subscribers for live dashboard display
    await manager.broadcast({
        "event": "object_detected",
        "session_code": event.session_code,
        "object_id": event.object_id,
        "class": event.class_name,
        "confidence": event.confidence,
        "bbox": event.bbox,
        "timestamp": event.timestamp
    })

    return DetectionEventResponse(
        id=record.id,
        session_id=record.session_id,
        object_id=record.object_id,
        timestamp=record.timestamp,
        class_name=record.class_name,
        confidence=record.confidence,
        bbox=[record.x1, record.y1, record.x2, record.y2]
    )


@router.post("/actions", response_model=TraineeActionResponse, status_code=status.HTTP_201_CREATED)
async def record_trainee_action(action: TraineeActionCreate, db: Session = Depends(get_db)):
    """Logs a trainee decision/identification response during simulation."""
    record = SessionService.record_action(db, action)

    # Broadcast action to WebSocket subscribers
    await manager.broadcast({
        "event": "trainee_response",
        "session_code": action.session_code,
        "object_id": action.object_id,
        "action": action.action,
        "correct": action.correct,
        "response_time": action.response_time
    })

    return record


# =====================================================================
# After-Action Review & History (Section 14 & 15)
# =====================================================================

@router.get("/aar/{session_code}", response_model=AARReportResponse)
async def get_aar_report(session_code: str, db: Session = Depends(get_db)):
    """Retrieves the After-Action Review (AAR) report for a completed session."""
    return SessionService.get_aar_report_response(db, session_code)


@router.get("/performance/{trainee_code}", response_model=PerformanceHistoryResponse)
async def get_trainee_performance(trainee_code: str, db: Session = Depends(get_db)):
    """Retrieves historical training performance across all sessions for a trainee."""
    return SessionService.get_performance_history(db, trainee_code)

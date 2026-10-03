"""
Training Session and Performance Scoring Service.
Manages session lifecycle, detection logs, trainee responses, and AAR generation.
"""

from datetime import datetime, timezone
import json
import os
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..database.models import (
    Trainee, Scenario, TrainingSession, DetectionRecord, TraineeAction, AARReport
)
from ..schemas.schemas import (
    SessionStartRequest, DetectionEventCreate, TraineeActionCreate,
    AARReportResponse, PerformanceHistoryResponse, PerformanceSessionItem
)
from .scenario_service import ScenarioService, ScenarioGenerateRequest


class SessionService:
    """Handles session state, event logging, and AAR score compilation."""

    # Default configurable weights matching Section 12
    DEFAULT_WEIGHTS = {
        "detection": 0.30,
        "classification": 0.30,
        "decision": 0.30,
        "response_time": 0.10
    }

    @classmethod
    def get_or_create_trainee(cls, db: Session, trainee_code: str, name: Optional[str] = None) -> Trainee:
        """Retrieves existing trainee or creates a new trainee record."""
        trainee = db.query(Trainee).filter(Trainee.trainee_code == trainee_code).first()
        if not trainee:
            trainee = Trainee(trainee_code=trainee_code, name=name or f"Trainee {trainee_code}")
            db.add(trainee)
            db.commit()
            db.refresh(trainee)
        return trainee

    @classmethod
    def start_session(cls, db: Session, req: SessionStartRequest) -> TrainingSession:
        """Initializes a new training session."""
        trainee = cls.get_or_create_trainee(db, req.trainee_code)

        if req.scenario_id:
            scenario = db.query(Scenario).filter(Scenario.id == req.scenario_id).first()
            if not scenario:
                raise HTTPException(status_code=404, detail=f"Scenario with ID {req.scenario_id} not found")
        else:
            # Generate a new scenario automatically
            gen_req = ScenarioGenerateRequest(difficulty=req.difficulty or "medium")
            scenario = ScenarioService.generate_scenario(db, gen_req)

        session_code = f"SES_{int(time.time() * 1000) % 1000000:06d}"

        session = TrainingSession(
            session_code=session_code,
            trainee_id=trainee.id,
            scenario_id=scenario.id,
            status="in_progress",
            start_time=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @classmethod
    def record_detection(cls, db: Session, event: DetectionEventCreate) -> DetectionRecord:
        """Stores an AI detection/tracking event into the database."""
        session = db.query(TrainingSession).filter(TrainingSession.session_code == event.session_code).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {event.session_code} not found")

        record = DetectionRecord(
            session_id=session.id,
            object_id=event.object_id,
            timestamp=event.timestamp,
            class_name=event.class_name,
            confidence=event.confidence,
            x1=event.bbox[0],
            y1=event.bbox[1],
            x2=event.bbox[2],
            y2=event.bbox[3]
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def record_action(cls, db: Session, action: TraineeActionCreate) -> TraineeAction:
        """Stores a trainee action / response into the database."""
        session = db.query(TrainingSession).filter(TrainingSession.session_code == action.session_code).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {action.session_code} not found")

        record = TraineeAction(
            session_id=session.id,
            object_id=action.object_id,
            action=action.action,
            timestamp=action.timestamp,
            correct=action.correct,
            response_time=action.response_time
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def end_session(cls, db: Session, session_code: str) -> AARReport:
        """
        Completes the session, calculates metrics across detection, classification,
        and decision adherence, and generates an AAR report (Section 12, 14).
        """
        session = db.query(TrainingSession).filter(TrainingSession.session_code == session_code).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_code} not found")

        if session.status == "completed" and session.aar_report:
            return session.aar_report

        session.status = "completed"
        session.end_time = datetime.now(timezone.utc)

        # Query events and actions
        detections = db.query(DetectionRecord).filter(DetectionRecord.session_id == session.id).all()
        actions = db.query(TraineeAction).filter(TraineeAction.session_id == session.id).all()
        scenario = session.scenario

        # Unique detected objects
        detected_obj_ids = set(d.object_id for d in detections)
        total_spawned = max(1, scenario.object_count)

        # 1. Detection Score: Trainee detected unique objects vs spawned
        detected_count = len(detected_obj_ids)
        detection_score = min(100.0, round((detected_count / total_spawned) * 100.0, 1))

        # 2. Classification & Decision Scores from trainee actions
        action_count = len(actions)
        correct_actions = sum(1 for a in actions if a.correct)

        if action_count > 0:
            decision_score = round((correct_actions / action_count) * 100.0, 1)
            classification_score = decision_score  # Base prototype alignment
            avg_resp_time = round(sum(a.response_time for a in actions) / action_count, 2)
            # Response score: higher score for faster response (e.g. within 5.0s = 100%)
            response_score = max(0.0, min(100.0, round((1.0 - min(avg_resp_time, 10.0) / 10.0) * 100.0, 1)))
        else:
            decision_score = 0.0
            classification_score = 0.0
            avg_resp_time = 0.0
            response_score = 0.0

        # Weighted composite score
        w = cls.DEFAULT_WEIGHTS
        overall_score = round(
            (detection_score * w["detection"]) +
            (classification_score * w["classification"]) +
            (decision_score * w["decision"]) +
            (response_score * w["response_time"]),
            1
        )

        session.overall_score = overall_score

        # Create or update AAR report
        aar = db.query(AARReport).filter(AARReport.session_id == session.id).first()
        if not aar:
            aar = AARReport(
                session_id=session.id,
                detection_score=detection_score,
                classification_score=classification_score,
                decision_score=decision_score,
                response_score=response_score,
                overall_score=overall_score,
                summary_notes=f"Scenario: {scenario.environment} / {scenario.lighting} / {scenario.difficulty}. Overall Score: {overall_score}%"
            )
            db.add(aar)

        db.commit()
        db.refresh(aar)
        return aar

    @classmethod
    def get_aar_report_response(cls, db: Session, session_code: str) -> AARReportResponse:
        """Retrieves and packages complete AAR report data."""
        session = db.query(TrainingSession).filter(TrainingSession.session_code == session_code).first()
        if not session or not session.aar_report:
            raise HTTPException(status_code=404, detail=f"AAR report for session {session_code} not found")

        aar = session.aar_report
        actions = db.query(TraineeAction).filter(TraineeAction.session_id == session.id).all()
        detections = db.query(DetectionRecord).filter(DetectionRecord.session_id == session.id).all()

        total_actions = len(actions)
        correct_actions = sum(1 for a in actions if a.correct)
        avg_resp = (sum(a.response_time for a in actions) / total_actions) if total_actions > 0 else 0.0

        return AARReportResponse(
            id=aar.id,
            session_code=session.session_code,
            trainee_code=session.trainee.trainee_code,
            scenario_code=session.scenario.scenario_code,
            environment=session.scenario.environment,
            lighting=session.scenario.lighting,
            difficulty=session.scenario.difficulty,
            duration=session.scenario.duration,
            detection_score=aar.detection_score,
            classification_score=aar.classification_score,
            decision_score=aar.decision_score,
            response_score=aar.response_score,
            overall_score=aar.overall_score,
            total_detections=len(detections),
            correct_actions=correct_actions,
            total_actions=total_actions,
            avg_response_time=round(avg_resp, 2),
            summary_notes=aar.summary_notes,
            created_at=aar.created_at
        )

    @classmethod
    def get_performance_history(cls, db: Session, trainee_code: str) -> PerformanceHistoryResponse:
        """Retrieves past session scores for a trainee (Section 15)."""
        trainee = db.query(Trainee).filter(Trainee.trainee_code == trainee_code).first()
        if not trainee:
            raise HTTPException(status_code=404, detail=f"Trainee {trainee_code} not found")

        completed_sessions = [
            s for s in trainee.sessions
            if s.status == "completed" and s.aar_report is not None
        ]
        completed_sessions.sort(key=lambda s: s.start_time)

        items: List[PerformanceSessionItem] = []
        total_score = 0.0

        for idx, s in enumerate(completed_sessions, start=1):
            aar = s.aar_report
            items.append(
                PerformanceSessionItem(
                    session_number=idx,
                    session_code=s.session_code,
                    date=s.start_time,
                    difficulty=s.scenario.difficulty,
                    detection_score=aar.detection_score,
                    classification_score=aar.classification_score,
                    decision_score=aar.decision_score,
                    overall_score=aar.overall_score
                )
            )
            total_score += aar.overall_score

        avg_score = round(total_score / len(items), 1) if items else 0.0

        return PerformanceHistoryResponse(
            trainee_code=trainee.trainee_code,
            total_sessions=len(items),
            average_score=avg_score,
            sessions=items
        )

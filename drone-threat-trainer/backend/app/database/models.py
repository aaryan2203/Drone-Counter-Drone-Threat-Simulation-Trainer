"""
SQLAlchemy ORM Models for Drone Threat Simulation Trainer.
Stores trainees, scenarios, training sessions, detection events,
trainee actions, and after-action review (AAR) reports.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Trainee(Base):
    """Registered trainee personnel."""
    __tablename__ = "trainees"

    id = Column(Integer, primary_key=True, index=True)
    trainee_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    sessions = relationship("TrainingSession", back_populates="trainee", cascade="all, delete-orphan")


class Scenario(Base):
    """Procedurally generated or configured training scenario."""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    scenario_code = Column(String(50), unique=True, index=True, nullable=False)
    environment = Column(String(50), nullable=False)   # urban, rural, open_terrain, industrial
    lighting = Column(String(50), nullable=False)      # day, night, low_light
    visibility = Column(String(50), nullable=False)    # clear, fog, reduced
    difficulty = Column(String(50), nullable=False)    # easy, medium, hard, expert
    object_count = Column(Integer, default=3, nullable=False)
    seed = Column(Integer, nullable=False)
    duration = Column(Integer, default=180, nullable=False)  # Duration in seconds
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    sessions = relationship("TrainingSession", back_populates="scenario")


class TrainingSession(Base):
    """An individual trainee practice session."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_code = Column(String(50), unique=True, index=True, nullable=False)
    trainee_id = Column(Integer, ForeignKey("trainees.id"), nullable=False)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    status = Column(String(30), default="in_progress", nullable=False)  # in_progress, completed, aborted
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_time = Column(DateTime, nullable=True)
    overall_score = Column(Float, nullable=True)

    trainee = relationship("Trainee", back_populates="sessions")
    scenario = relationship("Scenario", back_populates="sessions")
    detections = relationship("DetectionRecord", back_populates="session", cascade="all, delete-orphan")
    actions = relationship("TraineeAction", back_populates="session", cascade="all, delete-orphan")
    aar_report = relationship("AARReport", back_populates="session", uselist=False, cascade="all, delete-orphan")


class DetectionRecord(Base):
    """Perception event logged by the AI detection & tracking pipeline."""
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    object_id = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)  # Simulation time offset in seconds
    class_name = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    x1 = Column(Integer, nullable=False)
    y1 = Column(Integer, nullable=False)
    x2 = Column(Integer, nullable=False)
    y2 = Column(Integer, nullable=False)

    session = relationship("TrainingSession", back_populates="detections")


class TraineeAction(Base):
    """Decision and interaction submitted by the trainee during simulation."""
    __tablename__ = "trainee_actions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    object_id = Column(Integer, nullable=False)
    action = Column(String(80), nullable=False)  # e.g. "detect", "classify_drone", "respond_jam_rf"
    timestamp = Column(Float, nullable=False)
    correct = Column(Boolean, default=True, nullable=False)
    response_time = Column(Float, nullable=False)  # Seconds elapsed from spawn to action

    session = relationship("TrainingSession", back_populates="actions")


class AARReport(Base):
    """After-Action Review report generated upon session completion."""
    __tablename__ = "aar_reports"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), unique=True, nullable=False)
    detection_score = Column(Float, default=0.0, nullable=False)
    classification_score = Column(Float, default=0.0, nullable=False)
    decision_score = Column(Float, default=0.0, nullable=False)
    response_score = Column(Float, default=0.0, nullable=False)
    overall_score = Column(Float, default=0.0, nullable=False)
    summary_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("TrainingSession", back_populates="aar_report")

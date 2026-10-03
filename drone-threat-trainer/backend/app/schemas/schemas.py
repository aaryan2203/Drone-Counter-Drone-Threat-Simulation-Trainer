"""
Pydantic Schemas for Request & Response Data Validation.
Maintains strictly typed boundaries at API edges.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict


# =====================================================================
# 1. Trainee Schemas
# =====================================================================

class TraineeBase(BaseModel):
    trainee_code: str = Field(..., json_schema_extra={"example": "TRN-042"}, description="Unique identifier for trainee")
    name: Optional[str] = Field(None, json_schema_extra={"example": "Cadet Alex Vance"})


class TraineeCreate(TraineeBase):
    pass


class TraineeResponse(TraineeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# 2. Scenario Schemas
# =====================================================================

class ScenarioGenerateRequest(BaseModel):
    difficulty: Optional[str] = Field("medium", description="easy, medium, hard, expert, or random")
    environment: Optional[str] = Field(None, description="urban, rural, open_terrain, industrial, or random")
    lighting: Optional[str] = Field(None, description="day, night, low_light, or random")
    visibility: Optional[str] = Field(None, description="clear, fog, reduced, or random")
    object_count: Optional[int] = Field(None, ge=1, le=12, description="Target object count (1-12)")
    seed: Optional[int] = Field(None, description="Seed for deterministic reproduction")
    duration: Optional[int] = Field(180, ge=30, le=600, description="Scenario duration in seconds")


class ScenarioResponse(BaseModel):
    id: int
    scenario_code: str
    environment: str
    lighting: str
    visibility: str
    difficulty: str
    object_count: int
    seed: int
    duration: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# 3. Session Schemas
# =====================================================================

class SessionStartRequest(BaseModel):
    trainee_code: str = Field(..., json_schema_extra={"example": "TRN-042"})
    scenario_id: Optional[int] = Field(None, description="Existing scenario ID (or generate new if omitted)")
    difficulty: Optional[str] = Field("medium", description="Used if scenario_id is not provided")


class SessionEndRequest(BaseModel):
    session_code: str = Field(..., json_schema_extra={"example": "SES_001"})


class SessionResponse(BaseModel):
    id: int
    session_code: str
    trainee_code: str
    scenario_code: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    overall_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# 4. Perception & Detection Event Schemas (Section 6 & 13)
# =====================================================================

class DetectionEventCreate(BaseModel):
    session_code: str = Field(..., json_schema_extra={"example": "SES_001"})
    timestamp: float = Field(..., ge=0.0, description="Simulation timestamp in seconds")
    object_id: int = Field(..., description="Target object tracking ID")
    class_name: str = Field(..., json_schema_extra={"example": "drone"}, alias="class")
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: List[int] = Field(..., min_length=4, max_length=4, description="[x1, y1, x2, y2]")

    model_config = ConfigDict(populate_by_name=True)


class DetectionEventResponse(BaseModel):
    id: int
    session_id: int
    object_id: int
    timestamp: float
    class_name: str
    confidence: float
    bbox: List[int]

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# 5. Trainee Action Schemas
# =====================================================================

class TraineeActionCreate(BaseModel):
    session_code: str = Field(..., json_schema_extra={"example": "SES_001"})
    object_id: int = Field(..., description="Target ID interacted with")
    action: str = Field(
        ...,
        json_schema_extra={"example": "respond_jam_rf"},
        description="detect, identify_drone, identify_bird, respond_jam_rf, respond_alert_command, respond_log_only"
    )
    timestamp: float = Field(..., ge=0.0, description="Action timestamp")
    correct: bool = Field(True, description="Whether action aligned with scenario rule")
    response_time: float = Field(..., ge=0.0, description="Response time in seconds")


class TraineeActionResponse(BaseModel):
    id: int
    session_id: int
    object_id: int
    action: str
    timestamp: float
    correct: bool
    response_time: float

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# 6. After-Action Review (AAR) & Performance Schemas
# =====================================================================

class AARReportResponse(BaseModel):
    id: int
    session_code: str
    trainee_code: str
    scenario_code: str
    environment: str
    lighting: str
    difficulty: str
    duration: int
    detection_score: float
    classification_score: float
    decision_score: float
    response_score: float
    overall_score: float
    total_detections: int
    correct_actions: int
    total_actions: int
    avg_response_time: float
    summary_notes: Optional[str] = None
    created_at: datetime


class PerformanceSessionItem(BaseModel):
    session_number: int
    session_code: str
    date: datetime
    difficulty: str
    detection_score: float
    classification_score: float
    decision_score: float
    overall_score: float


class PerformanceHistoryResponse(BaseModel):
    trainee_code: str
    total_sessions: int
    average_score: float
    sessions: List[PerformanceSessionItem]

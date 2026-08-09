import shortuuid
from datetime import datetime
from typing import Literal
from sqlalchemy import Column, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from pydantic import BaseModel, ConfigDict, Field, field_validator

from database import Base

ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
id_generator = shortuuid.ShortUUID(alphabet=ID_ALPHABET)


def new_id(prefix):
    return f"{prefix}_{id_generator.random(length=8)}"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: new_id("usr"))
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(String, primary_key=True, default=lambda: new_id("rub"))
    title = Column(String, nullable=False)
    criteria = Column(JSON, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScoreCard(Base):
    __tablename__ = "scorecards"

    id = Column(String, primary_key=True, default=lambda: new_id("scr"))
    report_id = Column(String, nullable=False, index=True)
    rubric_id = Column(String, ForeignKey("rubrics.id"), nullable=False)
    raw_scores = Column(JSON, nullable=False)
    weighted_total = Column(Float, nullable=False)
    grade = Column(String, nullable=False)
    flags = Column(JSON, default=list)
    disagreements = Column(JSON, default=list)
    status = Column(String, default="complete")
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: new_id("aud"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class RubricCriterion(BaseModel):
    name: str
    description: str
    weight: float = Field(gt=0, le=100)


class RubricCreateRequest(BaseModel):
    title: str
    criteria: list[RubricCriterion]

    @field_validator("criteria")
    @classmethod
    def weights_sum_to_100(cls, criteria):
        total = sum(c.weight for c in criteria)
        if abs(total - 100) > 0.01:
            raise ValueError("criteria weights must sum to 100")
        return criteria


class RubricResponse(BaseModel):
    id: str
    title: str
    criteria: list[RubricCriterion]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CriterionScore(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    evidence_quote: str = Field(min_length=10)
    improvement_note: str
    confidence: float = Field(ge=0, le=1)


class DisagreementFlag(BaseModel):
    criterion_a: str
    criterion_b: str
    difference: float


class ScoreRequest(BaseModel):
    rubric_id: str
    report_text: str = Field(min_length=200)


class BatchScoreRequest(BaseModel):
    rubric_id: str
    reports: list[str] = Field(min_length=1, max_length=50)


class ScoreCardResponse(BaseModel):
    id: str
    report_id: str
    rubric_id: str
    raw_scores: list[CriterionScore]
    weighted_total: float
    grade: str
    flags: list[str]
    disagreements: list[DisagreementFlag]
    status: Literal["complete", "pending_review", "rejected"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchScoreResponse(BaseModel):
    scorecards: list[ScoreCardResponse]
    failed: list[dict]


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    user_id: str
    access_token: str
    token_type: str = "bearer"


class ExportMetadata(BaseModel):
    report_id: str
    rubric_id: str
    exported_at: datetime
    source: str = "e9"


class ExportScoreEntry(BaseModel):
    criterion: str
    score: float
    weight: float


class ExportJSON(BaseModel):
    metadata: ExportMetadata
    scores_array: list[ExportScoreEntry]
    total_grade: str
    total_percentage: float
    raw_quotes: dict[str, str]

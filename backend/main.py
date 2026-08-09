import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import database
from models import (
    User,
    UserRegister, UserLogin, TokenResponse,
    RubricCreateRequest, RubricResponse,
    ScoreRequest, ScoreCardResponse, BatchScoreRequest, BatchScoreResponse,
    new_id
)
from auth import hash_password, verify_password, create_access_token, get_current_user
from guardrails import input_guardrail, output_guardrail, GuardrailError
from math_utils import weighted_total, map_grade, detect_disagreements
from agents import run_orchestrator, json_export_agent

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="E9 Lab Report Rubric Scorer")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",")] if allowed_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=TokenResponse)
def register(payload: UserRegister, db: Session = Depends(database.get_db)):
    if database.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="username already taken")

    user = database.create_user(db, new_id("usr"), payload.username, hash_password(payload.password))
    token = create_access_token(user.id)
    return TokenResponse(user_id=user.id, access_token=token)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(database.get_db)):
    user = database.get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid username or password")

    token = create_access_token(user.id)
    return TokenResponse(user_id=user.id, access_token=token)


@app.post("/rubrics", response_model=RubricResponse)
def create_rubric_endpoint(payload: RubricCreateRequest, db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    criteria = [c.model_dump() for c in payload.criteria]
    rubric = database.create_rubric(db, new_id("rub"), payload.title, criteria, current_user.id)
    database.create_audit_log(db, new_id("aud"), current_user.id, "rubric_created", {"rubric_id": rubric.id})
    return rubric


@app.get("/rubrics", response_model=list[RubricResponse])
def list_rubrics_endpoint(db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    return database.list_rubrics(db, current_user.id)


@app.delete("/rubrics/{rubric_id}")
def delete_rubric_endpoint(rubric_id: str, db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    rubric = database.get_rubric(db, rubric_id, current_user.id)
    if not rubric:
        raise HTTPException(status_code=404, detail="rubric not found")
    database.delete_rubric(db, rubric)
    return {"deleted": rubric_id}


async def score_single_report(rubric, report_text, db, current_user):
    report_id = new_id("rpt")

    try:
        input_guardrail(report_text, rubric.criteria)
    except GuardrailError as e:
        database.create_audit_log(db, new_id("aud"), current_user.id, "input_guardrail_rejected", {"reason": str(e), "report_id": report_id})
        raise HTTPException(status_code=422, detail=str(e))

    scores = await run_orchestrator(rubric.criteria, report_text, report_id)

    try:
        output_guardrail(scores)
    except GuardrailError:
        scores = await run_orchestrator(rubric.criteria, report_text, report_id)
        try:
            output_guardrail(scores)
        except GuardrailError as retry_error:
            database.create_audit_log(db, new_id("aud"), current_user.id, "output_guardrail_rejected", {"reason": str(retry_error), "report_id": report_id})
            raise HTTPException(status_code=422, detail=str(retry_error))

    total = weighted_total(scores, rubric.criteria)
    grade = map_grade(total)
    disagreements = detect_disagreements(scores)
    flags = [f"{d['criterion_a']} vs {d['criterion_b']} differ by {d['difference']}" for d in disagreements]
    status = "pending_review" if disagreements else "complete"

    scorecard = database.create_scorecard(
        db,
        new_id("scr"),
        report_id,
        rubric.id,
        [s.model_dump() for s in scores],
        total,
        grade,
        flags,
        disagreements,
        status,
        current_user.id
    )
    database.create_audit_log(db, new_id("aud"), current_user.id, "report_scored", {"report_id": report_id, "scorecard_id": scorecard.id})

    return scorecard


@app.post("/score", response_model=ScoreCardResponse)
async def score_report(payload: ScoreRequest, db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    rubric = database.get_rubric(db, payload.rubric_id, current_user.id)
    if not rubric:
        raise HTTPException(status_code=404, detail="rubric not found")

    return await score_single_report(rubric, payload.report_text, db, current_user)


@app.post("/score/batch", response_model=BatchScoreResponse)
async def score_batch(payload: BatchScoreRequest, db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    rubric = database.get_rubric(db, payload.rubric_id, current_user.id)
    if not rubric:
        raise HTTPException(status_code=404, detail="rubric not found")

    scorecards = []
    failed = []
    for report_text in payload.reports:
        try:
            scorecard = await score_single_report(rubric, report_text, db, current_user)
            scorecards.append(scorecard)
        except HTTPException as e:
            failed.append({"error": e.detail})

    return BatchScoreResponse(scorecards=scorecards, failed=failed)


@app.get("/score/{report_id}/export")
async def export_scorecard(report_id: str, db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    scorecard = database.get_scorecard_by_report_id(db, report_id, current_user.id)
    if not scorecard:
        raise HTTPException(status_code=404, detail="scorecard not found")

    rubric = database.get_rubric_by_id(db, scorecard.rubric_id)
    export_data = await json_export_agent(scorecard, rubric.criteria)
    database.create_audit_log(db, new_id("aud"), current_user.id, "scorecard_exported", {"report_id": report_id})

    return export_data.model_dump()


@app.get("/score/{report_id}", response_model=ScoreCardResponse)
def get_scorecard(report_id: str, db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    scorecard = database.get_scorecard_by_report_id(db, report_id, current_user.id)
    if not scorecard:
        raise HTTPException(status_code=404, detail="scorecard not found")
    return scorecard


@app.get("/scorecards", response_model=list[ScoreCardResponse])
def list_scorecards(db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    return database.list_scorecards(db, current_user.id)


@app.get("/audit")
def get_audit_log(db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    logs = database.list_audit_logs(db, current_user.id)
    return [{"id": log.id, "action": log.action, "details": log.details, "timestamp": log.timestamp} for log in logs]

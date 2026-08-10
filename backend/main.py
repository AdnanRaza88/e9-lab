from fastapi import FastAPI, Depends, HTTPException
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import time
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()  # loads .env from the process working directory (repo root)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

import errors
from errors import AppError, error_response
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
from logger import logger

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="E9 Lab Report Rubric Scorer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    for err in exc.errors():
        loc = err.get("loc", [])
        msg = err.get("msg", "") or ""
        if "report" in str(loc).lower():
            if "too long" in msg or "70000" in msg:
                return JSONResponse(status_code=422, content=error_response(errors.LIMIT_EXCEEDED, errors.MESSAGES[errors.LIMIT_EXCEEDED]))
            if "too short" in msg:
                return JSONResponse(status_code=422, content=error_response(errors.REPORT_TOO_SHORT, errors.MESSAGES[errors.REPORT_TOO_SHORT]))
            if "empty" in msg:
                return JSONResponse(status_code=422, content=error_response(errors.EMPTY_INPUT, errors.MESSAGES[errors.EMPTY_INPUT]))
    return JSONResponse(status_code=422, content=error_response(errors.VALIDATION_ERROR, errors.MESSAGES[errors.VALIDATION_ERROR]))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = errors.STATUS_CODES.get(exc.status_code, errors.INVALID_REQUEST)
    return JSONResponse(status_code=exc.status_code, content=error_response(code, errors.MESSAGES[code]))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content=error_response(errors.SERVER_ERROR, errors.MESSAGES[errors.SERVER_ERROR]))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=TokenResponse)
def register(payload: UserRegister, db: Session = Depends(database.get_db)):
    if database.get_user_by_username(db, payload.username):
        raise AppError(errors.INVALID_REQUEST, "Username already taken.")

    user = database.create_user(db, new_id("usr"), payload.username, hash_password(payload.password))
    token = create_access_token(user.id)
    return TokenResponse(user_id=user.id, access_token=token)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(database.get_db)):
    user = database.get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise AppError(errors.INVALID_REQUEST, "Invalid username or password.", status_code=401)

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
    start = time.monotonic()
    logger.info("score_started", report_id=report_id, rubric_id=rubric.id,
                chars=len(report_text), criteria=len(rubric.criteria))

    try:
        input_guardrail(report_text, rubric.criteria)
    except GuardrailError as e:
        database.create_audit_log(db, new_id("aud"), current_user.id, "input_guardrail_rejected", {"reason": str(e), "report_id": report_id})
        raise AppError(errors.REPORT_TOO_SHORT if "below minimum" in str(e) else errors.EMPTY_INPUT)

    try:
        scores = await run_orchestrator(rubric.criteria, report_text, report_id)
    except Exception as exc:
        database.create_audit_log(db, new_id("aud"), current_user.id, "ai_scoring_failed", {"report_id": report_id, "error": str(exc)[:200]})
        logger.warning("score_failed", report_id=report_id, error=str(exc)[:300], elapsed_ms=round((time.monotonic() - start) * 1000))
        raise AppError(errors.AI_NOT_CONFIGURED if "GROQ_API_KEY" in str(exc) else (errors.TIMEOUT if errors.is_timeout(exc) else errors.AI_FAILURE))

    try:
        output_guardrail(scores)
    except GuardrailError:
        try:
            scores = await run_orchestrator(rubric.criteria, report_text, report_id)
            output_guardrail(scores)
        except GuardrailError as retry_error:
            database.create_audit_log(db, new_id("aud"), current_user.id, "output_guardrail_rejected", {"reason": str(retry_error), "report_id": report_id})
            raise AppError(errors.AI_FAILURE)
        except Exception as retry_exc:
            database.create_audit_log(db, new_id("aud"), current_user.id, "ai_scoring_failed", {"report_id": report_id, "error": str(retry_exc)[:200]})
            raise AppError(errors.AI_NOT_CONFIGURED if "GROQ_API_KEY" in str(retry_exc) else (errors.TIMEOUT if errors.is_timeout(retry_exc) else errors.AI_FAILURE))

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
    logger.info("score_completed", report_id=report_id, total=total, grade=grade,
                elapsed_ms=round((time.monotonic() - start) * 1000))

    return scorecard


@app.post("/score", response_model=ScoreCardResponse)
async def score_report(payload: ScoreRequest, db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    logger.info("score_request", report_chars=len(payload.report_text), rubric_id=payload.rubric_id, user_id=current_user.id)
    rubric = database.get_rubric(db, payload.rubric_id, current_user.id)
    if not rubric:
        raise AppError(errors.RUBRIC_REQUIRED)

    return await score_single_report(rubric, payload.report_text, db, current_user)


@app.post("/score/batch", response_model=BatchScoreResponse)
async def score_batch(payload: BatchScoreRequest, db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    rubric = database.get_rubric(db, payload.rubric_id, current_user.id)
    if not rubric:
        raise AppError(errors.RUBRIC_REQUIRED)

    scorecards = []
    failed = []
    for report_text in payload.reports:
        try:
            scorecard = await score_single_report(rubric, report_text, db, current_user)
            scorecards.append(scorecard)
        except AppError as e:
            failed.append({"error": e.message})

    return BatchScoreResponse(scorecards=scorecards, failed=failed)


@app.get("/scorecards", response_model=list[ScoreCardResponse])
def list_scorecards_endpoint(db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    return database.list_scorecards(db, current_user.id)


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


@app.get("/audit")
def get_audit_log(db: Session = Depends(database.get_db), current_user: User = Depends(get_current_user)):
    logs = database.list_audit_logs(db, current_user.id)
    return [{"id": log.id, "action": log.action, "details": log.details, "timestamp": log.timestamp} for log in logs]


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def catch_all_404(request: Request, full_path: str):
    # Serve the static frontend (login/app pages) — same origin as the API,
    # so Railway serves the whole app from one process/URL.
    if request.method in ("GET", "HEAD"):
        if full_path == "":
            target = FRONTEND_DIR / "index.html"
        else:
            target = (FRONTEND_DIR / full_path).resolve()
        if target.is_file() and target.is_relative_to(FRONTEND_DIR.resolve()):
            return FileResponse(target)
    return JSONResponse(status_code=404, content=error_response(errors.NOT_FOUND, errors.MESSAGES[errors.NOT_FOUND]))

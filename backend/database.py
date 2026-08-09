import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./e9.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


import models


def create_user(db, user_id, username, hashed_password):
    user = models.User(id=user_id, username=username, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db, username):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_id(db, user_id):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_rubric(db, rubric_id, title, criteria, user_id):
    rubric = models.Rubric(id=rubric_id, title=title, criteria=criteria, user_id=user_id)
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return rubric


def list_rubrics(db, user_id):
    return db.query(models.Rubric).filter(models.Rubric.user_id == user_id).order_by(models.Rubric.created_at.desc()).all()


def get_rubric(db, rubric_id, user_id):
    return db.query(models.Rubric).filter(models.Rubric.id == rubric_id, models.Rubric.user_id == user_id).first()


def get_rubric_by_id(db, rubric_id):
    return db.query(models.Rubric).filter(models.Rubric.id == rubric_id).first()


def delete_rubric(db, rubric):
    db.delete(rubric)
    db.commit()


def create_scorecard(db, scorecard_id, report_id, rubric_id, raw_scores, weighted_total, grade, flags, disagreements, status, user_id):
    scorecard = models.ScoreCard(
        id=scorecard_id,
        report_id=report_id,
        rubric_id=rubric_id,
        raw_scores=raw_scores,
        weighted_total=weighted_total,
        grade=grade,
        flags=flags,
        disagreements=disagreements,
        status=status,
        user_id=user_id
    )
    db.add(scorecard)
    db.commit()
    db.refresh(scorecard)
    return scorecard


def get_scorecard_by_report_id(db, report_id, user_id):
    return db.query(models.ScoreCard).filter(models.ScoreCard.report_id == report_id, models.ScoreCard.user_id == user_id).first()


def list_scorecards(db, user_id):
    return db.query(models.ScoreCard).filter(models.ScoreCard.user_id == user_id).order_by(models.ScoreCard.created_at.desc()).all()


def create_audit_log(db, log_id, user_id, action, details):
    entry = models.AuditLog(id=log_id, user_id=user_id, action=action, details=details)
    db.add(entry)
    db.commit()
    return entry


def list_audit_logs(db, user_id):
    return db.query(models.AuditLog).filter(models.AuditLog.user_id == user_id).order_by(models.AuditLog.timestamp.desc()).all()

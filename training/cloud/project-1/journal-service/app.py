from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv(Path(__file__).with_name(".env"))

from database import Base, engine, get_db
from models import Journal
from security import decode_access_token

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HabitFlow Journal Service", version="1.0.0")


class JournalCreate(BaseModel):
    title: str
    content: str


class JournalUpdate(BaseModel):
    title: str
    content: str


def get_current_user_id(authorization: Optional[str]) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    return int(decode_access_token(token))


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "journal"}


@app.post("/journal")
def create_journal(payload: JournalCreate, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    journal = Journal(user_id=user_id, title=payload.title.strip(), content=payload.content.strip())
    db.add(journal)
    db.commit()
    db.refresh(journal)
    return journal


@app.get("/journal")
def list_journals(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    journals = db.query(Journal).filter(Journal.user_id == user_id).order_by(Journal.created_at.desc()).all()
    return journals


@app.put("/journal/{journal_id}")
def update_journal(journal_id: int, payload: JournalUpdate, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    journal = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")

    journal.title = payload.title.strip()
    journal.content = payload.content.strip()
    db.commit()
    db.refresh(journal)
    return journal


@app.delete("/journal/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(journal_id: int, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    journal = db.query(Journal).filter(Journal.id == journal_id, Journal.user_id == user_id).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")

    db.delete(journal)
    db.commit()

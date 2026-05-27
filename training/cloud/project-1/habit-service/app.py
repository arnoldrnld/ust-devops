import calendar
from datetime import date
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv(Path(__file__).with_name(".env"))

from database import Base, engine, get_db
from models import Habit, HabitEntry, User
from security import decode_access_token

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HabitFlow Habit Service", version="1.0.0")


class HabitCreate(BaseModel):
    name: str


class HabitUpdate(BaseModel):
    name: str


class HabitTrack(BaseModel):
    date: date
    completed: bool = True


def get_current_user_id(authorization: Optional[str]) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    return int(decode_access_token(token))


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "habit"}


@app.post("/habits")
def create_habit(payload: HabitCreate, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    habit = Habit(user_id=user_id, name=payload.name.strip())
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return {"id": habit.id, "name": habit.name, "created_at": habit.created_at}


@app.get("/habits")
def list_habits(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    habits = db.query(Habit).filter(Habit.user_id == user_id).order_by(Habit.created_at.asc()).all()
    return [{"id": h.id, "name": h.name, "created_at": h.created_at} for h in habits]


@app.put("/habits/{habit_id}")
def rename_habit(habit_id: int, payload: HabitUpdate, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    habit.name = payload.name.strip()
    db.commit()
    db.refresh(habit)
    return {"id": habit.id, "name": habit.name}


@app.delete("/habits/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(habit_id: int, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    db.delete(habit)
    db.commit()


@app.post("/habits/{habit_id}/track")
def track_habit(habit_id: int, payload: HabitTrack, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    entry = db.query(HabitEntry).filter(HabitEntry.habit_id == habit_id, HabitEntry.date == payload.date).first()
    if entry:
        entry.completed = payload.completed
    else:
        entry = HabitEntry(habit_id=habit_id, date=payload.date, completed=payload.completed)
        db.add(entry)

    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "habit_id": entry.habit_id, "date": entry.date, "completed": entry.completed}


@app.get("/habits/month")
def habits_month(year: int, month: int, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_current_user_id(authorization)
    _, days_in_month = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, days_in_month)

    habits = db.query(Habit).filter(Habit.user_id == user_id).order_by(Habit.created_at.asc()).all()

    response = []
    for habit in habits:
        entries = (
            db.query(HabitEntry)
            .filter(HabitEntry.habit_id == habit.id, HabitEntry.date >= start_date, HabitEntry.date <= end_date)
            .all()
        )
        entry_map = {e.date.day: e.completed for e in entries}
        grid = [{"day": day, "completed": entry_map.get(day, False)} for day in range(1, days_in_month + 1)]
        response.append({"habit_id": habit.id, "name": habit.name, "grid": grid})

    return {"year": year, "month": month, "days": days_in_month, "habits": response}

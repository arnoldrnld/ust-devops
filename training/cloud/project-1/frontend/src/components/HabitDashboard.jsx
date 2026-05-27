import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";

export default function HabitDashboard({ token }) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [newHabit, setNewHabit] = useState("");
  const [data, setData] = useState({ habits: [], days: 30 });

  const monthName = useMemo(() => new Date(year, month - 1, 1).toLocaleString("default", { month: "long" }), [year, month]);
  const currentDay =
    now.getFullYear() === year && now.getMonth() + 1 === month
      ? now.getDate()
      : null;

  async function load() {
    const res = await api.monthHabits(year, month, token);
    setData(res);
  }

  useEffect(() => {
    load();
  }, [year, month]);

  async function addHabit(e) {
    e.preventDefault();
    if (!newHabit.trim()) return;
    await api.createHabit({ name: newHabit }, token);
    setNewHabit("");
    load();
  }

  async function renameHabit(habit) {
    const name = window.prompt("Rename habit", habit.name);
    if (!name) return;
    await api.renameHabit(habit.habit_id, { name }, token);
    load();
  }

  async function removeHabit(habitId) {
    if (!window.confirm("Delete this habit?")) return;
    await api.deleteHabit(habitId, token);
    load();
  }

  async function toggle(habitId, day, current) {
    const d = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    await api.trackHabit(habitId, { date: d, completed: !current }, token);
    load();
  }

  return (
    <div className="card dashboard-card">
      <div className="section-head">
        <h2>Habit Dashboard</h2>
        <p>Track consistency day by day.</p>
      </div>

      <div className="row controls-row">
        <label htmlFor="month-select">Month:</label>
        <select id="month-select" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
          {Array.from({ length: 12 }, (_, idx) => idx + 1).map((m) => (
            <option key={m} value={m}>
              {new Date(year, m - 1, 1).toLocaleString("default", { month: "long" })}
            </option>
          ))}
        </select>
        <input type="number" min="2020" max="2100" value={year} onChange={(e) => setYear(Number(e.target.value))} />
        <span className="month-pill">{monthName}</span>
      </div>

      <form onSubmit={addHabit} className="row add-habit-row">
        <input value={newHabit} onChange={(e) => setNewHabit(e.target.value)} placeholder="Add habit" />
        <button className="add-btn">Add</button>
      </form>

      <div className="table-wrap">
        <table className="habit-grid-table">
          <thead>
            <tr>
              <th className="habit-col">Habits</th>
              {Array.from({ length: data.days }, (_, idx) => idx + 1).map((day) => (
                <th key={day} className={currentDay === day ? "today-head" : ""}>{day}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.habits.map((habit) => (
              <tr key={habit.habit_id}>
                <td className="habit-col habit-meta-cell">
                  <strong>{habit.name}</strong>
                  <div className="habit-actions">
                    <button className="row-action-btn" title="Rename habit" aria-label="Rename habit" onClick={() => renameHabit(habit)}>Rename</button>
                    <button className="row-action-btn danger" title="Delete habit" aria-label="Delete habit" onClick={() => removeHabit(habit.habit_id)}>Delete</button>
                  </div>
                </td>
                {habit.grid.map((entry) => (
                  <td key={entry.day} className="day-cell-wrap">
                    <button
                      className={`day-cell ${entry.completed ? "done" : ""} ${currentDay === entry.day ? "today" : ""}`}
                      onClick={() => toggle(habit.habit_id, entry.day, entry.completed)}
                      title={`Day ${entry.day}`}
                    >
                      {entry.completed ? "" : ""}
                    </button>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

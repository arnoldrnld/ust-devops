import { config } from "./config";

async function request(path, method = "GET", body = null, token = null) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${config.API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  register: (payload) => request("/auth/register", "POST", payload),
  login: (payload) => request("/auth/login", "POST", payload),
  me: (token) => request("/auth/me", "GET", null, token),

  listHabits: (token) => request("/habits", "GET", null, token),
  createHabit: (payload, token) => request("/habits", "POST", payload, token),
  renameHabit: (id, payload, token) => request(`/habits/${id}`, "PUT", payload, token),
  deleteHabit: (id, token) => request(`/habits/${id}`, "DELETE", null, token),
  trackHabit: (id, payload, token) => request(`/habits/${id}/track`, "POST", payload, token),
  monthHabits: (year, month, token) => request(`/habits/month?year=${year}&month=${month}`, "GET", null, token),

  listJournals: (token) => request("/journal", "GET", null, token),
  createJournal: (payload, token) => request("/journal", "POST", payload, token),
  updateJournal: (id, payload, token) => request(`/journal/${id}`, "PUT", payload, token),
  deleteJournal: (id, token) => request(`/journal/${id}`, "DELETE", null, token),
};

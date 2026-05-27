import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function JournalPage({ token }) {
  const [entries, setEntries] = useState([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  async function load() {
    const res = await api.listJournals(token);
    setEntries(res);
  }

  useEffect(() => {
    load();
  }, []);

  async function addEntry(e) {
    e.preventDefault();
    await api.createJournal({ title, content }, token);
    setTitle("");
    setContent("");
    load();
  }

  async function editEntry(entry) {
    const newTitle = window.prompt("Edit title", entry.title);
    if (!newTitle) return;
    const newContent = window.prompt("Edit content", entry.content);
    if (!newContent) return;
    await api.updateJournal(entry.id, { title: newTitle, content: newContent }, token);
    load();
  }

  async function removeEntry(id) {
    if (!window.confirm("Delete this entry?")) return;
    await api.deleteJournal(id, token);
    load();
  }

  return (
    <div className="card journal-card">
      <div className="section-head">
        <h2>Journal Timeline</h2>
        <p>Capture your wins, thoughts, and reflections.</p>
      </div>
      <form onSubmit={addEntry} className="journal-form">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Entry title" required />
        <textarea value={content} onChange={(e) => setContent(e.target.value)} placeholder="Write your thoughts" required />
        <button className="add-btn">Add Entry</button>
      </form>
      <div className="timeline">
        {entries.map((entry) => (
          <div key={entry.id} className="timeline-item">
            <h3>{entry.title}</h3>
            <small>{new Date(entry.created_at).toLocaleString()}</small>
            <p>{entry.content}</p>
            <div className="entry-actions">
              <button className="icon-btn" title="Edit entry" aria-label="Edit entry" onClick={() => editEntry(entry)}>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 17.25V20h2.75L17.8 8.95l-2.75-2.75L4 17.25zM19.71 7.04a1 1 0 0 0 0-1.42l-1.34-1.33a1 1 0 0 0-1.41 0l-1.13 1.13 2.75 2.75 1.13-1.13z" />
                </svg>
              </button>
              <button className="icon-btn danger" title="Delete entry" aria-label="Delete entry" onClick={() => removeEntry(entry.id)}>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 7h12l-1 14H7L6 7zm3-3h6l1 2h4v2H4V6h4l1-2z" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

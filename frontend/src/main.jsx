import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API = "http://localhost:8000";

function App() {
  const [employees, setEmployees] = useState([]);
  const [dashboard, setDashboard] = useState({});
  const [selected, setSelected] = useState("");
  const [tasks, setTasks] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [message, setMessage] = useState("");

  async function load() {
    try {
      const [e, d] = await Promise.all([
        fetch(`${API}/employees`).then(r => r.json()),
        fetch(`${API}/dashboard`).then(r => r.json())
      ]);
      setEmployees(e);
      setDashboard(d);
      if (!selected && e.length) setSelected(String(e[0].id));
    } catch {
      setMessage("Cannot reach the API. Start the backend at http://localhost:8000.");
    }
  }

  async function loadTasks(id) {
    if (!id) return;
    const response = await fetch(`${API}/employees/${id}/tasks`);
    setTasks(await response.json());
  }

  useEffect(() => { load(); }, []);
  useEffect(() => { if (selected) loadTasks(selected); }, [selected]);

  async function generateChecklist() {
    const response = await fetch(`${API}/employees/${selected}/generate-checklist`, { method: "POST" });
    const data = await response.json();
    setMessage(`Checklist generated. ${data.created_count ?? 0} new tasks added.`);
    loadTasks(selected);
    load();
  }

  async function askPolicy(e) {
    e.preventDefault();
    setAnswer(null);
    setMessage("Searching approved policy content...");
    const response = await fetch(`${API}/assistant/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 5 })
    });
    const data = await response.json();
    if (!response.ok) {
      setMessage(data.detail || "Assistant request failed.");
      return;
    }
    setAnswer(data);
    setMessage("");
  }

  return (
    <main className="shell">
      <header>
        <div>
          <p className="eyebrow">HR OPERATIONS · HACKATHON MVP</p>
          <h1>Onboarding command center</h1>
          <p className="sub">Track employee readiness, checklist tasks, and policy questions.</p>
        </div>
        <button className="secondary" onClick={load}>Refresh data</button>
      </header>

      {message && <div className="notice">{message}</div>}

      <section className="stats">
        <article><span>Employees</span><strong>{dashboard.employee_count ?? 0}</strong></article>
        <article><span>Checklist tasks</span><strong>{dashboard.task_count ?? 0}</strong></article>
        <article><span>Completed</span><strong>{dashboard.completed ?? 0}</strong></article>
        <article><span>Pending</span><strong>{dashboard.pending ?? 0}</strong></article>
        <article><span>Overdue</span><strong>{dashboard.overdue ?? 0}</strong></article>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div><p className="eyebrow">EMPLOYEE WORKSPACE</p><h2>Onboarding checklist</h2></div>
          <div className="actions">
            <select value={selected} onChange={e => setSelected(e.target.value)}>
              <option value="">Select employee</option>
              {employees.map(e => <option key={e.id} value={e.id}>{e.name} · {e.department}</option>)}
            </select>
            <button disabled={!selected} onClick={generateChecklist}>Generate checklist</button>
          </div>
        </div>
        {tasks.length === 0 ? <p className="empty">Choose an employee and generate their checklist.</p> : (
          <div className="task-list">
            {tasks.map(t => (
              <article className="task" key={t.id}>
                <div>
                  <strong>{t.title}</strong>
                  <p>{t.task_type} · Owner: {t.owner_team} · Due: {t.due_date}</p>
                  <small>Why added: {t.rule_explanation}</small>
                </div>
                <span className={`status ${t.overdue ? "late" : ""}`}>{t.overdue ? "Overdue" : t.status}</span>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <p className="eyebrow">POLICY RAG ASSISTANT</p>
        <h2>Ask an HR policy question</h2>
        <form className="ask" onSubmit={askPolicy}>
          <input value={question} onChange={e => setQuestion(e.target.value)} placeholder="e.g. What documents should I submit before joining?" required />
          <button type="submit">Ask assistant</button>
        </form>
        {answer && <div className="answer">
          <h3>Answer</h3>
          <p>{typeof answer.answer === "string" ? answer.answer : JSON.stringify(answer.answer)}</p>
          <h3>Retrieved sources</h3>
          {answer.sources?.length ? <ul>{answer.sources.map((s, i) => <li key={i}>{s.policy_title}{s.page_number ? ` · Page ${s.page_number}` : ""}</li>)}</ul> : <p>No approved source was retrieved.</p>}
        </div>}
      </section>

      <section className="panel">
        <p className="eyebrow">EMPLOYEE ROSTER</p>
        <h2>New joiners</h2>
        <div className="roster">
          {employees.map(e => <button className="person" key={e.id} onClick={() => setSelected(String(e.id))}>
            <strong>{e.name}</strong><span>{e.role} · {e.department}</span><small>{e.location} · Joining {e.joining_date}</small>
          </button>)}
          {!employees.length && <p className="empty">No employees yet. Add one using the API docs at /docs.</p>}
        </div>
      </section>
      <footer>Demo application · Use synthetic employee data only.</footer>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);

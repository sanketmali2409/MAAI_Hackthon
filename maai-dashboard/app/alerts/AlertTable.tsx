"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import type { Escalation } from "@/lib/api";

function fmt(ts: string | null): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export default function AlertTable({ initial }: { initial: Escalation[] }) {
  const router = useRouter();
  const [rows, setRows] = useState<Escalation[]>(initial);
  const [busy, setBusy] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  async function update(id: string, status: string) {
    setBusy(id);
    try {
      const res = await fetch(`/api/v1/epds/escalations/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, notes: notes[id] || undefined }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const updated = await res.json();
      setRows((rs) => rs.map((r) => (r.id === id ? updated : r)));
      router.refresh();
    } catch (e) {
      alert("Failed to update alert.");
    } finally {
      setBusy(null);
    }
  }

  if (rows.length === 0) return <div className="empty">No alerts.</div>;

  return (
    <table>
      <thead>
        <tr><th>Reason</th><th>Risk</th><th>Score</th><th>Status</th><th>Session</th><th>Created</th><th>Follow-up</th></tr>
      </thead>
      <tbody>
        {rows.map((e) => (
          <tr key={e.id}>
            <td><span className="badge high">{e.reason.replace("_", " ")}</span></td>
            <td><span className={`badge ${e.risk_band || "none"}`}>{e.risk_band || "—"}</span></td>
            <td>{e.total_score ?? "—"}</td>
            <td><span className={`badge ${e.status}`}>{e.status}</span></td>
            <td>{e.session_id ? <Link className="muted" href={`/sessions/${e.session_id}`}>view</Link> : "—"}</td>
            <td>{fmt(e.created_at)}</td>
            <td>
              {e.status === "resolved" ? (
                <span className="muted">{e.notes || "resolved"}</span>
              ) : (
                <div className="row">
                  <input
                    placeholder="note / next action"
                    value={notes[e.id] ?? e.notes ?? ""}
                    onChange={(ev) => setNotes((n) => ({ ...n, [e.id]: ev.target.value }))}
                    style={{ background: "var(--bg)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 6, padding: "4px 8px", width: 160 }}
                  />
                  {e.status === "open" && (
                    <button className="btn secondary" disabled={busy === e.id} onClick={() => update(e.id, "acknowledged")}>Acknowledge</button>
                  )}
                  <button className="btn" disabled={busy === e.id} onClick={() => update(e.id, "resolved")}>Resolve</button>
                </div>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

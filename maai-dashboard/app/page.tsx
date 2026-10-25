import Link from "next/link";
import { listSessions, listEscalations, listMothers } from "@/lib/api";
import { RiskBadge, StatusBadge, FlagBadge, fmt } from "./ui";

export const dynamic = "force-dynamic";

export default async function Overview() {
  let sessions, escalations, mothers;
  try {
    [sessions, escalations, mothers] = await Promise.all([
      listSessions(),
      listEscalations(),
      listMothers(),
    ]);
  } catch (e: any) {
    return (
      <main className="container">
        <h1>Overview</h1>
        <p className="empty">Backend unreachable. Is the MAAI API running and AGENTLINE_API_KEY set? ({e.message})</p>
      </main>
    );
  }

  const completed = sessions.filter((s) => s.status === "completed");
  const incomplete = sessions.filter((s) => s.status === "in_progress");
  const openAlerts = escalations.filter((e) => e.status === "open");
  const dueSoon = mothers.filter(
    (m) => m.active && m.next_call_at && new Date(m.next_call_at) <= new Date()
  );

  return (
    <main className="container">
      <h1>Overview</h1>
      <p className="sub">Screening activity across your account, from persisted records.</p>

      <div className="cards">
        <div className="card"><div className="num">{dueSoon.length}</div><div className="label">Calls due now</div></div>
        <div className="card"><div className="num">{completed.length}</div><div className="label">Completed screenings</div></div>
        <div className="card"><div className="num">{incomplete.length}</div><div className="label">Incomplete screenings</div></div>
        <div className="card"><div className="num">{openAlerts.length}</div><div className="label">Alerts awaiting review</div></div>
        <div className="card"><div className="num">{mothers.length}</div><div className="label">Registered mothers</div></div>
      </div>

      <h2>Alerts awaiting review</h2>
      {openAlerts.length === 0 ? (
        <div className="empty">No open alerts.</div>
      ) : (
        <table>
          <thead><tr><th>Reason</th><th>Risk</th><th>Score</th><th>Created</th><th>Session</th></tr></thead>
          <tbody>
            {openAlerts.map((e) => (
              <tr key={e.id}>
                <td><span className="badge high">{e.reason.replace("_", " ")}</span></td>
                <td><RiskBadge band={e.risk_band} /></td>
                <td>{e.total_score ?? "—"}</td>
                <td>{fmt(e.created_at)}</td>
                <td>{e.session_id ? <Link href={`/sessions/${e.session_id}`} className="muted">{e.session_id}</Link> : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Recent screenings</h2>
      {sessions.length === 0 ? (
        <div className="empty">No screenings yet.</div>
      ) : (
        <table>
          <thead><tr><th>Mother</th><th>Status</th><th>Risk</th><th>Score</th><th>Flag</th><th>Created</th></tr></thead>
          <tbody>
            {sessions.slice(0, 25).map((s) => (
              <tr key={s.id}>
                <td><Link href={`/sessions/${s.id}`}>{s.subject_name || s.subject_phone || s.id}</Link></td>
                <td><StatusBadge status={s.status} /></td>
                <td><RiskBadge band={s.risk_band} /></td>
                <td>{s.total_score ?? "—"}</td>
                <td><FlagBadge on={s.self_harm_flag} /></td>
                <td>{fmt(s.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}

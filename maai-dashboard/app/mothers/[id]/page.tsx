import Link from "next/link";
import { getMother, getConsentHistory } from "@/lib/api";
import { RiskBadge, StatusBadge, FlagBadge, fmt } from "../../ui";

export const dynamic = "force-dynamic";

export default async function MotherProfile({ params }: { params: { id: string } }) {
  let data, consentHistory;
  try {
    [data, consentHistory] = await Promise.all([
      getMother(params.id),
      getConsentHistory(params.id),
    ]);
  } catch (e: any) {
    return <main className="container"><h1>Mother</h1><p className="empty">Could not load profile ({e.message}).</p></main>;
  }
  const { mother, has_active_consent, sessions } = data;

  return (
    <main className="container">
      <h1>{mother.name || mother.id}</h1>
      <p className="sub">{mother.phone} · {mother.language} · {mother.call_cadence}</p>

      <div className="panel">
        <div className="kv">
          <div className="k">Active consent</div><div>{has_active_consent ? <span className="badge resolved">yes</span> : <span className="badge open">no</span>}</div>
          <div className="k">Enrolled</div><div>{mother.active ? "active" : "inactive"}</div>
          <div className="k">Next call</div><div>{fmt(mother.next_call_at)}</div>
          <div className="k">Registered</div><div>{fmt(mother.created_at)}</div>
          {mother.notes ? (<><div className="k">Notes</div><div>{mother.notes}</div></>) : null}
        </div>
      </div>

      <h2>Consent history</h2>
      {consentHistory.length === 0 ? (
        <div className="empty">No consent records.</div>
      ) : (
        <table>
          <thead><tr><th>Consented</th><th>Scope</th><th>Method</th><th>Recorded</th><th>Revoked</th></tr></thead>
          <tbody>
            {consentHistory.map((c) => (
              <tr key={c.id}>
                <td>{c.consented ? "granted" : <span className="muted">withdrawn</span>}</td>
                <td>{c.scope || "—"}</td>
                <td>{c.method || "—"}</td>
                <td>{fmt(c.recorded_at)}</td>
                <td>{fmt(c.revoked_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Screening history</h2>
      {sessions.length === 0 ? (
        <div className="empty">No screenings for this mother.</div>
      ) : (
        <table>
          <thead><tr><th>Session</th><th>Status</th><th>Risk</th><th>Score</th><th>Flag</th><th>Date</th></tr></thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td><Link href={`/sessions/${s.id}`}>{s.id}</Link></td>
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

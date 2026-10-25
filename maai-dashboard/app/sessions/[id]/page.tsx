import Link from "next/link";
import { getSession } from "@/lib/api";
import { RiskBadge, StatusBadge, FlagBadge, fmt } from "../../ui";

export const dynamic = "force-dynamic";

export default async function SessionDetail({ params }: { params: { id: string } }) {
  let data;
  try {
    data = await getSession(params.id);
  } catch (e: any) {
    return <main className="container"><h1>Screening</h1><p className="empty">Could not load session ({e.message}).</p></main>;
  }
  const { session, result, answers } = data;

  return (
    <main className="container">
      <h1>Screening {session.id}</h1>
      <p className="sub">{session.subject_name || "—"} · {session.subject_phone || "no phone"} · {session.language}</p>

      <div className="panel">
        <div className="kv">
          <div className="k">Status</div><div><StatusBadge status={session.status} /></div>
          <div className="k">Risk band</div><div><RiskBadge band={session.risk_band} /> <FlagBadge on={session.self_harm_flag} /></div>
          <div className="k">Total score</div><div>{session.total_score ?? "—"} / 30</div>
          <div className="k">Answered</div><div>{result?.answered ?? 0} / 10</div>
          <div className="k">Started</div><div>{fmt(session.created_at)}</div>
          <div className="k">Completed</div><div>{fmt(session.completed_at)}</div>
          <div className="k">Mother</div><div>{session.mother_id ? <Link className="muted" href={`/mothers/${session.mother_id}`}>{session.mother_id}</Link> : "—"}</div>
        </div>
      </div>

      <h2>Answers</h2>
      <table>
        <thead><tr><th>Q</th><th>Answer index</th><th>Item score</th></tr></thead>
        <tbody>
          {Array.from({ length: 10 }, (_, i) => i + 1).map((q) => (
            <tr key={q}>
              <td>Q{q}{q === 10 ? " (self-harm)" : ""}</td>
              <td>{answers[String(q)] ?? <span className="muted">not answered</span>}</td>
              <td>{result?.per_question?.[String(q)] ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Call transcript</h2>
      {session.transcript ? (
        <div className="transcript">{session.transcript}</div>
      ) : (
        <div className="empty">No transcript recorded for this call.</div>
      )}
    </main>
  );
}

import Link from "next/link";
import { listMothers } from "@/lib/api";
import { fmt } from "../ui";

export const dynamic = "force-dynamic";

export default async function Mothers() {
  let mothers;
  try {
    mothers = await listMothers();
  } catch (e: any) {
    return <main className="container"><h1>Mothers</h1><p className="empty">Could not load mothers ({e.message}).</p></main>;
  }

  return (
    <main className="container">
      <h1>Registered mothers</h1>
      <p className="sub">Mothers enrolled for screening calls.</p>
      {mothers.length === 0 ? (
        <div className="empty">No mothers registered yet.</div>
      ) : (
        <table>
          <thead><tr><th>Name</th><th>Phone</th><th>Language</th><th>Cadence</th><th>Next call</th><th>Active</th></tr></thead>
          <tbody>
            {mothers.map((m) => (
              <tr key={m.id}>
                <td><Link href={`/mothers/${m.id}`}>{m.name || m.id}</Link></td>
                <td>{m.phone}</td>
                <td>{m.language}</td>
                <td>{m.call_cadence}</td>
                <td>{fmt(m.next_call_at)}</td>
                <td>{m.active ? "yes" : <span className="muted">no</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}

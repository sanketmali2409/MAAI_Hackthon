import { listEscalations } from "@/lib/api";
import AlertTable from "./AlertTable";

export const dynamic = "force-dynamic";

export default async function Alerts() {
  let escalations;
  try {
    escalations = await listEscalations();
  } catch (e: any) {
    return <main className="container"><h1>Alert queue</h1><p className="empty">Could not load alerts ({e.message}).</p></main>;
  }

  const open = escalations.filter((e) => e.status !== "resolved");
  const resolved = escalations.filter((e) => e.status === "resolved");

  return (
    <main className="container">
      <h1>Alert queue</h1>
      <p className="sub">Self-harm and high-risk escalations. Acknowledge, add a next action, then resolve.</p>

      <h2>Needs attention ({open.length})</h2>
      <AlertTable initial={open} />

      <h2>Resolved ({resolved.length})</h2>
      <AlertTable initial={resolved} />
    </main>
  );
}

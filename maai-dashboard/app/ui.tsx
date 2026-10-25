export function RiskBadge({ band }: { band: string | null }) {
  const b = band || "none";
  return <span className={`badge ${b}`}>{band || "—"}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${status}`}>{status.replace("_", " ")}</span>;
}

export function FlagBadge({ on }: { on: boolean }) {
  if (!on) return null;
  return <span className="badge flag">self-harm</span>;
}

export function fmt(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

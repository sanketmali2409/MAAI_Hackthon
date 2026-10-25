import { NextRequest, NextResponse } from "next/server";

// Server-side proxy to the AgentLine/MAAI FastAPI backend. The API key lives
// only in server env (AGENTLINE_API_KEY) and is attached here, so it never
// reaches the browser bundle. The clinician dashboard calls /api/... and this
// forwards to {AGENTLINE_BASE_URL}/... with authentication.

const BASE = process.env.AGENTLINE_BASE_URL || "http://localhost:8000";
const KEY = process.env.AGENTLINE_API_KEY || "";

// Only these backend path prefixes may be reached through the dashboard proxy.
const ALLOWED = ["v1/epds", "v1/mothers"];

function targetUrl(req: NextRequest, path: string[]): string | null {
  const joined = path.join("/");
  if (!ALLOWED.some((p) => joined === p || joined.startsWith(p + "/"))) {
    return null;
  }
  const qs = req.nextUrl.search || "";
  return `${BASE.replace(/\/$/, "")}/${joined}${qs}`;
}

async function forward(req: NextRequest, path: string[]) {
  const url = targetUrl(req, path);
  if (!url) {
    return NextResponse.json({ error: "Path not allowed." }, { status: 403 });
  }
  const init: RequestInit = {
    method: req.method,
    headers: {
      Authorization: `Bearer ${KEY}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }
  try {
    const resp = await fetch(url, init);
    const text = await resp.text();
    return new NextResponse(text, {
      status: resp.status,
      headers: { "Content-Type": resp.headers.get("Content-Type") || "application/json" },
    });
  } catch (e: any) {
    return NextResponse.json({ error: `Backend unreachable: ${e.message}` }, { status: 502 });
  }
}

type Ctx = { params: { path: string[] } };

export async function GET(req: NextRequest, { params }: Ctx) {
  return forward(req, params.path);
}
export async function POST(req: NextRequest, { params }: Ctx) {
  return forward(req, params.path);
}
export async function PATCH(req: NextRequest, { params }: Ctx) {
  return forward(req, params.path);
}
export async function DELETE(req: NextRequest, { params }: Ctx) {
  return forward(req, params.path);
}

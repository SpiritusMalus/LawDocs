import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  if (!UUID_RE.test(id)) return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  try {
    const result = await authFetch(`/api/v1/orders/${id}`);
    if (!result.ok) return result.error;
    const data = await result.res.json();
    return NextResponse.json(data, { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

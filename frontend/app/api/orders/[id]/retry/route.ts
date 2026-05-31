import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";
import { isValidUuid } from "@/lib/validators";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  if (!isValidUuid(id)) return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  try {
    const result = await authFetch(`/api/v1/orders/${id}/retry`, { method: "POST" });
    if (!result.ok) return result.error;
    const data = await result.res.json();
    return NextResponse.json(data, { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

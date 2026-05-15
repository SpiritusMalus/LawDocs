import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  console.log("[pay] cookie present:", !!token, "| token prefix:", token?.slice(0, 20));
  try {
    const result = await authFetch(`/api/v1/orders/${id}/pay`, { method: "POST" });
    console.log("[pay] authFetch result.ok:", result.ok);
    if (!result.ok) return result.error;
    const data = await result.res.json();
    console.log("[pay] backend status:", result.res.status, "| body:", JSON.stringify(data));
    return NextResponse.json(data, { status: result.res.status });
  } catch (e) {
    console.error("[pay] exception:", e);
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

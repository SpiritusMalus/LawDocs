import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL = process.env.BACKEND_URL ?? "";

export async function GET(request: NextRequest) {
  const cookieStore = await cookies();
  const adminToken = cookieStore.get("admin_token")?.value;
  if (!adminToken) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const period = request.nextUrl.searchParams.get("period") ?? "week";

  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/admin/stats?period=${encodeURIComponent(period)}`, {
      headers: { "X-Admin-Token": adminToken },
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

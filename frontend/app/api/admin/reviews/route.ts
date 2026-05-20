import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "";

export async function GET(request: NextRequest) {
  const secret = request.headers.get("x-admin-secret");
  if (!secret) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/reviews/admin`, {
      headers: { "X-Admin-Secret": secret },
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

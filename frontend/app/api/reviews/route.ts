import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

const BACKEND_URL = process.env.BACKEND_URL ?? "";

// GET — публичный, без авторизации
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const params = new URLSearchParams();
  if (searchParams.get("page")) params.set("page", searchParams.get("page")!);
  if (searchParams.get("limit")) params.set("limit", searchParams.get("limit")!);
  if (searchParams.get("situation")) params.set("situation", searchParams.get("situation")!);

  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/reviews?${params}`, {
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

// POST — требует авторизации
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const result = await authFetch("/api/v1/reviews/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!result.ok) return result.error;
    const data = await result.res.json();
    return NextResponse.json(data, { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const result = await authFetch("/api/v1/auth/setup-e2ee", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!result.ok) return result.error;

  const data = await result.res.json();
  return NextResponse.json(data, { status: result.res.status });
}

import { NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

export async function GET() {
  try {
    const result = await authFetch("/api/v1/auth/me/contact");
    if (!result.ok) return result.error;
    const data = await result.res.json();
    return NextResponse.json(data, { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

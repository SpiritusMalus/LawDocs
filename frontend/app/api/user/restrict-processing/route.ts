import { NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

export async function POST() {
  try {
    const result = await authFetch("/api/v1/users/me/restrict-processing", { method: "POST" });
    if (!result.ok) return result.error;
    const data = await result.res.json();
    return NextResponse.json(data, { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

export async function DELETE() {
  try {
    const result = await authFetch("/api/v1/users/me/restrict-processing", { method: "DELETE" });
    if (!result.ok) return result.error;
    const data = await result.res.json();
    return NextResponse.json(data, { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

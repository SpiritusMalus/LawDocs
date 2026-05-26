import { NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

export async function GET() {
  try {
    const result = await authFetch("/api/v1/users/me/data-export");
    if (!result.ok) return result.error;
    const data = await result.res.json();
    return NextResponse.json(data, {
      status: 200,
      headers: {
        "Content-Disposition": 'attachment; filename="my-data.json"',
      },
    });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { isValidUuid } from "@/lib/validators";

const BACKEND_URL = process.env.BACKEND_URL ?? "";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const cookieStore = await cookies();
  const secret = cookieStore.get("admin_token")?.value;
  if (!secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { id } = await params;
  if (!isValidUuid(id)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/reviews/${id}/visibility`, {
      method: "PATCH",
      headers: { "X-Admin-Secret": secret },
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

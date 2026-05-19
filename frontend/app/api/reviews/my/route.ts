import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

export async function GET(request: NextRequest) {
  const orderId = new URL(request.url).searchParams.get("order_id");
  if (!orderId) return NextResponse.json({ error: "missing_order_id" }, { status: 400 });

  try {
    const result = await authFetch(`/api/v1/reviews/my?order_id=${orderId}`);
    if (!result.ok) return result.error;
    const data = await result.res.json();
    return NextResponse.json(data, { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

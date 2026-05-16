import { NextRequest, NextResponse } from "next/server";

// Dev-only endpoint: simulates ЮKassa payment.succeeded webhook
export async function POST(request: NextRequest) {
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.json({ error: "backend not configured" }, { status: 503 });
  }

  const { order_id } = (await request.json()) as { order_id: string };
  if (!order_id) {
    return NextResponse.json({ error: "order_id required" }, { status: 400 });
  }

  try {
    const res = await fetch(`${backendUrl}/api/v1/webhooks/yookassa`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event: "payment.succeeded",
        object: { id: `dev_${order_id}` },
      }),
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

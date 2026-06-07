import { NextRequest, NextResponse } from "next/server";

/**
 * Прокси к бэкенду за challenge для логина по ключу. Сервер возвращает nonce,
 * зашифрованный публичным ключом — расшифровать сможет только владелец приватного.
 */
export async function POST(request: NextRequest) {
  const { public_key } = (await request.json().catch(() => ({}))) as {
    public_key?: string;
  };

  if (!public_key) {
    return NextResponse.json({ error: "missing_public_key" }, { status: 400 });
  }

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }

  try {
    const res = await fetch(`${backendUrl}/api/v1/auth/key-challenge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ public_key }),
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json({ error: "challenge_failed" }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
}

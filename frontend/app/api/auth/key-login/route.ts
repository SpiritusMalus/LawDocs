import { NextRequest, NextResponse } from "next/server";

/**
 * Логин по решённому challenge. Прокси на бэкенд; на успехе ставит httpOnly
 * access_token-cookie на домене фронта (как verify/confirm/route.ts).
 */
export async function POST(request: NextRequest) {
  const { challenge_id, nonce } = (await request.json().catch(() => ({}))) as {
    challenge_id?: string;
    nonce?: string;
  };

  if (!challenge_id || !nonce) {
    return NextResponse.json({ error: "missing_fields" }, { status: 400 });
  }

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }

  try {
    const res = await fetch(`${backendUrl}/api/v1/auth/key-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ challenge_id, nonce }),
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json({ error: "login_failed" }, { status: res.status });
    }

    const { access_token } = (await res.json()) as { access_token: string };

    const response = NextResponse.json({ redirectTo: "/dashboard" });
    response.cookies.set("access_token", access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60,
    });
    return response;
  } catch {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
}

import { NextRequest, NextResponse } from "next/server";

interface KeyringEntry {
  public_key: string;
  wrapped_private_key: string;
  label: string | null;
}

/**
 * Логин email+паролем. Прокси на бэкенд; ставит httpOnly access_token-cookie и
 * возвращает фронту keyring — браузер раскроет ключи паролем локально.
 */
export async function POST(request: NextRequest) {
  const { email, password } = (await request.json().catch(() => ({}))) as {
    email?: string;
    password?: string;
  };

  if (!email || !password) {
    return NextResponse.json({ error: "missing_fields" }, { status: 400 });
  }

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }

  try {
    const res = await fetch(`${backendUrl}/api/v1/auth/password-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json({ error: "login_failed" }, { status: res.status });
    }

    const { access_token, keyring } = (await res.json()) as {
      access_token: string;
      keyring: KeyringEntry[];
    };

    const response = NextResponse.json({ redirectTo: "/dashboard", keyring });
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

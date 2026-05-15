import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60, // matches ACCESS_TOKEN_EXPIRE_MINUTES
};

type AuthFetchResult =
  | { ok: true; res: Response }
  | { ok: false; error: NextResponse };

/**
 * Authenticated fetch to the backend with sliding session support.
 * Reads access_token cookie, forwards as Bearer, and refreshes the cookie
 * if the backend returns X-Refresh-Token (token is close to expiry).
 */
export async function authFetch(
  path: string,
  options: RequestInit = {}
): Promise<AuthFetchResult> {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return { ok: false, error: NextResponse.json({ error: "unavailable" }, { status: 503 }) };
  }

  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) {
    return { ok: false, error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  }

  const res = await fetch(`${backendUrl}${path}`, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  const newToken = res.headers.get("x-refresh-token");
  if (newToken) {
    cookieStore.set("access_token", newToken, COOKIE_OPTIONS);
  }

  return { ok: true, res };
}

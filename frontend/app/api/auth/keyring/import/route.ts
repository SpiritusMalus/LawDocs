import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

/**
 * Импорт ключ-файлов в keyring под паролем аккаунта (объединение ключей).
 * Требует входа (cookie форвардится через authFetch). wrapped_private_key уже
 * зашифрован паролем на клиенте — сервер его не читает.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const result = await authFetch("/api/v1/auth/keyring/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!result.ok) return result.error;
    return NextResponse.json(await result.res.json(), { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

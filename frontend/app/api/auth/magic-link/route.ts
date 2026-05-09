import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.json({ error: "Сервис недоступен" }, { status: 503 });
  }

  let email: string;
  try {
    const body = await request.json();
    email = body.email?.trim();
  } catch {
    return NextResponse.json({ error: "Неверный запрос" }, { status: 400 });
  }

  if (!email) {
    return NextResponse.json({ error: "Введите email" }, { status: 400 });
  }

  try {
    const res = await fetch(`${backendUrl}/api/v1/auth/magic-link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json({ error: "Не удалось отправить письмо" }, { status: res.status });
    }

    return NextResponse.json({ ok: true }, { status: 200 });
  } catch {
    return NextResponse.json({ error: "Ошибка сервера" }, { status: 500 });
  }
}

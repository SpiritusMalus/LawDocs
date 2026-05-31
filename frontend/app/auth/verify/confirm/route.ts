import { NextRequest, NextResponse } from "next/server";
import { isValidUuid } from "@/lib/validators";

/**
 * POST-подтверждение magic-link. Вызывается кнопкой со страницы /auth/verify
 * (не на загрузке), поэтому почтовые сканеры/антивирусы — которые делают только
 * предпросмотр через GET — не «съедают» одноразовый токен до клика юзера.
 *
 * Делает POST на бэкенд, ставит httpOnly-cookie на нужном домене фронта и
 * возвращает фронту, куда редиректить дальше.
 */
export async function POST(request: NextRequest) {
  const { token, order } = (await request.json().catch(() => ({}))) as {
    token?: string;
    order?: string;
  };

  if (!token) {
    return NextResponse.json({ error: "missing_token" }, { status: 400 });
  }

  const orderId = order && isValidUuid(order) ? order : null;

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }

  try {
    const params = new URLSearchParams({ token });
    if (orderId) params.set("order", orderId);

    const res = await fetch(`${backendUrl}/api/v1/auth/verify?${params}`, {
      method: "POST",
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json({ error: "invalid_link" }, { status: 400 });
    }

    const { access_token, order_id } = (await res.json()) as {
      access_token: string;
      order_id: string | null;
    };

    // После входа ведём на setup-e2ee: страница сама решит, нужна ли настройка
    // ключей (проверит localStorage) и пропустит её, если ключи уже есть.
    const finalDest = order_id && isValidUuid(order_id) ? `/orders/${order_id}` : "/";
    const redirectTo = `/setup-e2ee?next=${encodeURIComponent(finalDest)}`;

    const response = NextResponse.json({ redirectTo });
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

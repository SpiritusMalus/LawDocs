import { NextRequest, NextResponse } from "next/server";
import { isValidUuid } from "@/lib/validators";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const token = searchParams.get("token");
  const rawOrderId = searchParams.get("order");
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://law-docs.ru";

  if (!token) {
    return NextResponse.redirect(new URL("/auth/error?reason=missing_token", baseUrl));
  }

  const orderId = rawOrderId && isValidUuid(rawOrderId) ? rawOrderId : null;

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.redirect(new URL("/auth/error?reason=unavailable", baseUrl));
  }

  try {
    const params = new URLSearchParams({ token });
    if (orderId) params.set("order", orderId);

    const res = await fetch(`${backendUrl}/api/v1/auth/verify?${params}`, {
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.redirect(new URL("/auth/error?reason=invalid_link", baseUrl));
    }

    const { access_token, order_id } = (await res.json()) as {
      access_token: string;
      order_id: string | null;
    };

    // После входа направляем на setup-e2ee: страница проверит localStorage
    // и либо пропустит настройку (ключи уже есть), либо покажет wizard настройки.
    const finalDest = order_id && isValidUuid(order_id) ? `/orders/${order_id}` : "/";
    const redirectTo = `/setup-e2ee?next=${encodeURIComponent(finalDest)}`;
    const response = NextResponse.redirect(new URL(redirectTo, baseUrl));
    response.cookies.set("access_token", access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60,
    });
    return response;
  } catch {
    return NextResponse.redirect(new URL("/auth/error?reason=unavailable", baseUrl));
  }
}

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { isValidUuid } from "@/lib/validators";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const token = searchParams.get("token");
  const rawOrderId = searchParams.get("order");

  if (!token) {
    return NextResponse.redirect(new URL("/auth/error?reason=missing_token", request.url));
  }

  // Validate orderId to prevent open-redirect / path injection
  const orderId = rawOrderId && isValidUuid(rawOrderId) ? rawOrderId : null;

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return NextResponse.redirect(new URL("/auth/error?reason=unavailable", request.url));
  }

  try {
    const params = new URLSearchParams({ token });
    if (orderId) params.set("order", orderId);

    const res = await fetch(`${backendUrl}/api/v1/auth/verify?${params}`, {
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.redirect(new URL("/auth/error?reason=invalid_link", request.url));
    }

    const { access_token, order_id } = (await res.json()) as {
      access_token: string;
      order_id: string | null;
    };

    const cookieStore = await cookies();
    cookieStore.set("access_token", access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 7,
    });

    const redirectTo =
      order_id && isValidUuid(order_id) ? `/orders/${order_id}` : "/";
    return NextResponse.redirect(new URL(redirectTo, request.url));
  } catch {
    return NextResponse.redirect(new URL("/auth/error?reason=unavailable", request.url));
  }
}

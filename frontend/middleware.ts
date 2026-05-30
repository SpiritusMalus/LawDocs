import { NextRequest, NextResponse } from "next/server";

const ALLOWED_ORIGINS = new Set([
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://law-docs.ru",
  "http://localhost:3000",
]);

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Protect /admin/* pages (except /admin/login itself)
  if (pathname.startsWith("/admin/") && pathname !== "/admin/login") {
    const adminToken = request.cookies.get("admin_token")?.value;
    if (!adminToken) {
      const loginUrl = request.nextUrl.clone();
      loginUrl.pathname = "/admin/login";
      loginUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Allow GET and HEAD requests
  if (request.method === "GET" || request.method === "HEAD") {
    return NextResponse.next();
  }

  // For POST, PUT, DELETE: check Origin header
  const origin = request.headers.get("origin");

  // For /api/admin/* mutations: Origin header is required
  const isAdminMutation =
    request.nextUrl.pathname.startsWith("/api/admin/") &&
    request.method !== "GET" &&
    request.method !== "HEAD";

  if (isAdminMutation && !origin) {
    return NextResponse.json(
      { error: "Forbidden: origin required for admin mutations" },
      { status: 403 }
    );
  }

  // Allow requests without Origin header (same-origin requests from Server Actions, server-to-server)
  // But reject requests with Origin that doesn't match our allowed list
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return NextResponse.json(
      { error: "Forbidden: cross-origin request not allowed" },
      { status: 403 }
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/api/:path*", "/admin/:path*"],
};

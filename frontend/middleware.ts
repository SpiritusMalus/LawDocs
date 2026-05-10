import { NextRequest, NextResponse } from "next/server";

const ALLOWED_ORIGINS = new Set([
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://law-docs.ru",
  "http://localhost:3000",
]);

export function middleware(request: NextRequest) {
  // Allow GET and HEAD requests
  if (request.method === "GET" || request.method === "HEAD") {
    return NextResponse.next();
  }

  // For POST, PUT, DELETE: check Origin header
  const origin = request.headers.get("origin");

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
  matcher: "/api/:path*",
};

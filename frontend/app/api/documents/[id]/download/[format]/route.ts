import { cookies } from "next/headers";
import { NextRequest } from "next/server";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; format: string }> }
) {
  const { id, format } = await params;

  if (format !== "docx" && format !== "pdf") {
    return new Response(JSON.stringify({ error: "invalid_format" }), { status: 400 });
  }

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    return new Response(JSON.stringify({ error: "unavailable" }), { status: 503 });
  }

  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) {
    return new Response(JSON.stringify({ error: "unauthorized" }), { status: 401 });
  }

  try {
    const res = await fetch(`${backendUrl}/api/v1/documents/${id}/download/${format}`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      return new Response(JSON.stringify({ error: "not_ready" }), { status: res.status });
    }

    const contentType =
      res.headers.get("content-type") ?? "application/octet-stream";
    const disposition =
      res.headers.get("content-disposition") ??
      `attachment; filename="document.${format}"`;

    return new Response(res.body, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": disposition,
      },
    });
  } catch {
    return new Response(JSON.stringify({ error: "upstream_error" }), { status: 502 });
  }
}

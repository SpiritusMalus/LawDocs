import { NextRequest } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; format: string }> }
) {
  const { id, format } = await params;

  if (!UUID_RE.test(id)) return new Response(JSON.stringify({ error: "invalid_id" }), { status: 400 });
  if (format !== "docx" && format !== "pdf") {
    return new Response(JSON.stringify({ error: "invalid_format" }), { status: 400 });
  }

  try {
    const result = await authFetch(`/api/v1/documents/${id}/download/${format}`);
    if (!result.ok) return result.error;

    if (!result.res.ok) {
      return new Response(JSON.stringify({ error: "not_ready" }), { status: result.res.status });
    }

    const contentType =
      result.res.headers.get("content-type") ?? "application/octet-stream";
    const disposition =
      result.res.headers.get("content-disposition") ??
      `attachment; filename="document.${format}"`;

    return new Response(result.res.body, {
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

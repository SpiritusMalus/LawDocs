import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";
import { isValidUuid } from "@/lib/validators";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; format: string }> }
) {
  const { id, format } = await params;

  if (!isValidUuid(id)) return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  if (format !== "docx" && format !== "pdf") {
    return NextResponse.json({ error: "invalid_format" }, { status: 400 });
  }

  try {
    const result = await authFetch(`/api/v1/documents/${id}/download/${format}`);
    if (!result.ok) return result.error;

    if (!result.res.ok) {
      return NextResponse.json({ error: "not_ready" }, { status: result.res.status });
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
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

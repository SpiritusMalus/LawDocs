import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; format: string }> }
) {
  const { id, format } = await params;

  if (!UUID_RE.test(id)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  if (format !== "docx" && format !== "pdf") {
    return NextResponse.json({ error: "invalid_format" }, { status: 400 });
  }

  const result = await authFetch(`/api/v1/documents/${id}/download-info/${format}`);
  if (!result.ok) return result.error;

  if (!result.res.ok) {
    return new Response(result.res.body, { status: result.res.status });
  }

  const data = await result.res.json();
  return NextResponse.json(data);
}

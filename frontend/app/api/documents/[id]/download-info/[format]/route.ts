import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";
import { isValidUuid } from "@/lib/validators";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; format: string }> }
) {
  const { id, format } = await params;

  if (!isValidUuid(id)) {
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

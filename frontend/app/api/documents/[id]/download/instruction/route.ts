import { NextRequest } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";
import { isValidUuid } from "@/lib/validators";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  if (!isValidUuid(id)) return new Response(JSON.stringify({ error: "invalid_id" }), { status: 400 });

  try {
    const result = await authFetch(`/api/v1/documents/${id}/download/instruction`);
    if (!result.ok) return result.error;

    if (!result.res.ok) {
      return new Response(JSON.stringify({ error: "not_ready" }), { status: result.res.status });
    }

    const contentType = result.res.headers.get("content-type") ?? "application/pdf";
    const disposition =
      result.res.headers.get("content-disposition") ?? `attachment; filename="instrukciya.pdf"`;

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

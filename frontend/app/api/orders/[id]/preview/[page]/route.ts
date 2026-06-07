import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";
import { isValidUuid } from "@/lib/validators";

/**
 * Прокси одной watermarked-PNG страницы превью. Бэкенд сам качает картинку из S3
 * и стримит её — браузер грузит same-origin, без зависимости от S3-ссылок/CORS.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; page: string }> }
) {
  const { id, page } = await params;
  if (!isValidUuid(id)) return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  if (!/^\d+$/.test(page)) return NextResponse.json({ error: "invalid_page" }, { status: 400 });

  try {
    const result = await authFetch(`/api/v1/orders/${id}/preview/${page}`);
    if (!result.ok) return result.error;

    const buf = await result.res.arrayBuffer();
    return new NextResponse(buf, {
      status: result.res.status,
      headers: {
        "Content-Type": result.res.headers.get("content-type") ?? "image/png",
        "Cache-Control": "private, max-age=60",
      },
    });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

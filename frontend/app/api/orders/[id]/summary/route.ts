import { NextRequest, NextResponse } from "next/server";
import { authFetch } from "@/lib/proxy-fetch";
import { isValidUuid } from "@/lib/validators";

/** Сводка введённых полей заказа (метка → значение) для сверки на превью. */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  if (!isValidUuid(id)) return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  try {
    const result = await authFetch(`/api/v1/orders/${id}/summary`);
    if (!result.ok) return result.error;
    return NextResponse.json(await result.res.json(), { status: result.res.status });
  } catch {
    return NextResponse.json({ error: "upstream_error" }, { status: 502 });
  }
}

import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/stats/documents-count`, {
      next: { revalidate: 3600 },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ count: 0 }, { status: 200 });
  }
}

import { ImageResponse } from "next/og";
import { getSituationPage } from "@/lib/situation-pages";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = getSituationPage(slug);

  const title = page?.h1 ?? "Юридический документ";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          backgroundImage:
            "linear-gradient(135deg, #f8fafc 0%, #eff6ff 50%, #dbeafe 100%)",
          fontFamily: "sans-serif",
        }}
      >
        {/* Logo row */}
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div
            style={{
              display: "flex",
              width: 56,
              height: 56,
              borderRadius: 12,
              background: "#2563eb",
              color: "#fff",
              fontSize: 26,
              fontWeight: 700,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            LD
          </div>
          <div
            style={{ display: "flex", fontSize: 36, fontWeight: 600, color: "#0f172a" }}
          >
            LawDocs
          </div>
        </div>

        {/* Main content */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div
            style={{
              display: "flex",
              fontSize: 64,
              fontWeight: 700,
              color: "#0f172a",
              lineHeight: 1.1,
              letterSpacing: "-0.02em",
              maxWidth: 900,
            }}
          >
            {title}
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 30,
              color: "#475569",
              lineHeight: 1.4,
            }}
          >
            Готовый документ со ссылками на законы — 500 rub
          </div>
        </div>

        {/* Footer row */}
        <div style={{ display: "flex", gap: 32, fontSize: 22, color: "#64748b" }}>
          <div style={{ display: "flex" }}>Word + PDF</div>
          <div style={{ display: "flex" }}>Законодательная база</div>
          <div style={{ display: "flex" }}>Инструкция куда нести</div>
        </div>
      </div>
    ),
    { ...size }
  );
}

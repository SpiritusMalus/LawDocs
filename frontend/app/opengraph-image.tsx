import { ImageResponse } from "next/og";

export const alt = "LawDocs — готовый юридический документ за 5 минут, 199 ₽";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
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
          <div style={{ display: "flex", fontSize: 36, fontWeight: 600, color: "#0f172a" }}>
            LawDocs
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
          <div
            style={{
              display: "flex",
              fontSize: 72,
              fontWeight: 700,
              color: "#0f172a",
              lineHeight: 1.05,
              letterSpacing: "-0.02em",
            }}
          >
            Готовый юридический документ за 5 минут — 199 ₽
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 30,
              color: "#475569",
              lineHeight: 1.4,
              maxWidth: 920,
            }}
          >
            Претензия в магазин, банк, к работодателю или страховой —
            оформленная по всем правилам. Шаблоны проверены юристом.
          </div>
        </div>

        <div style={{ display: "flex", gap: 32, fontSize: 22, color: "#64748b" }}>
          <div style={{ display: "flex" }}>Word + PDF</div>
          <div style={{ display: "flex" }}>Расчёт неустойки</div>
          <div style={{ display: "flex" }}>Инструкция куда нести</div>
        </div>
      </div>
    ),
    { ...size }
  );
}

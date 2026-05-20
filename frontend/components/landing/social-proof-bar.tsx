import { FileText } from "lucide-react";

const BACKEND_URL = process.env.BACKEND_URL ?? "";

async function getDocumentsCount(): Promise<number> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/stats/documents-count`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return 0;
    const data = await res.json();
    return typeof data.count === "number" ? data.count : 0;
  } catch {
    return 0;
  }
}

export async function SocialProofBar() {
  const count = await getDocumentsCount();
  if (count === 0) return null;

  return (
    <div className="bg-blue-50 border-b border-blue-100 py-3 px-4">
      <div className="max-w-(--l-content) mx-auto flex items-center justify-center gap-2 text-sm text-blue-700">
        <FileText className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>
          <strong>{count.toLocaleString("ru-RU")}</strong> документов составлено с 2026 года
        </span>
      </div>
    </div>
  );
}

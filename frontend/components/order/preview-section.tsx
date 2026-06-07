"use client";

import { useEffect, useState } from "react";
import { Loader2, Eye } from "lucide-react";
import { fetchPreview } from "@/lib/api-client";

// Показывает watermarked-превью документа ДО оплаты. Это растровые PNG с
// водяным знаком — текст не выделяется и не копируется; чистый файл придёт
// только после оплаты.
export function PreviewSection({ orderId }: { orderId: string }) {
  const [pages, setPages] = useState<string[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await fetchPreview(orderId);
        if (!res.ok) {
          if (active) setError(true);
          return;
        }
        const data: { pages: string[] } = await res.json();
        if (active) setPages(data.pages ?? []);
      } catch {
        if (active) setError(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [orderId]);

  if (error) return null;

  if (pages === null) {
    return (
      <div className="flex items-center justify-center gap-2 py-6 text-sm text-gray-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Готовим предпросмотр…
      </div>
    );
  }

  if (pages.length === 0) return null;

  return (
    <div className="space-y-3 text-left">
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Eye className="h-4 w-4 text-gray-400" />
        Предпросмотр документа. После оплаты скачаете чистый файл без водяного знака.
      </div>
      <div className="space-y-3">
        {pages.map((url, i) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={i}
            src={url}
            alt={`Страница ${i + 1}`}
            draggable={false}
            className="w-full rounded-lg border border-gray-200 shadow-sm select-none pointer-events-none"
          />
        ))}
      </div>
    </div>
  );
}

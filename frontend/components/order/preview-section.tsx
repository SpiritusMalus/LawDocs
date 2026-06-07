"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Eye, Maximize2, ImageOff, X, ChevronLeft, ChevronRight } from "lucide-react";
import { fetchPreview } from "@/lib/api-client";

// Показывает watermarked-превью документа ДО оплаты. Это растровые PNG с водяным
// знаком — текст не выделяется и не копируется (это картинка, а не текст; чистый
// файл придёт только после оплаты). Клик по странице открывает её крупно в модалке.
//
// Намеренно НЕ блокируем правый клик / PrintScreen: это обходится и выглядит
// любительски (см. design-решение). Защита — водяной знак, а не блокировки.
export function PreviewSection({ orderId }: { orderId: string }) {
  const [pages, setPages] = useState<string[] | null>(null);
  const [error, setError] = useState(false);
  const [broken, setBroken] = useState<Set<number>>(new Set());
  const [openAt, setOpenAt] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError(false);
    setBroken(new Set());
    try {
      const res = await fetchPreview(orderId);
      if (!res.ok) {
        setError(true);
        return;
      }
      const data: { page_count: number } = await res.json();
      // Картинки грузим через бэкенд-прокси (same-origin), а не по S3-ссылке.
      // ?r=timestamp — cache-buster, чтобы «Обновить» перегрузило ранее битый кадр.
      const count = data.page_count ?? 0;
      const bust = Date.now();
      setPages(Array.from({ length: count }, (_, i) => `/api/orders/${orderId}/preview/${i}?r=${bust}`));
    } catch {
      setError(true);
    }
  }, [orderId]);

  useEffect(() => {
    let active = true;
    (async () => {
      await load();
      if (!active) return;
    })();
    return () => {
      active = false;
    };
  }, [load]);

  // Управление модалкой с клавиатуры: Esc — закрыть, стрелки — листать.
  useEffect(() => {
    if (openAt === null || !pages) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpenAt(null);
      if (e.key === "ArrowRight") setOpenAt((i) => (i === null ? i : Math.min(i + 1, pages!.length - 1)));
      if (e.key === "ArrowLeft") setOpenAt((i) => (i === null ? i : Math.max(i - 1, 0)));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openAt, pages]);

  if (error) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-500">
        Не удалось загрузить предпросмотр.{" "}
        <button onClick={load} className="text-blue-600 hover:underline">
          Обновить
        </button>
      </div>
    );
  }

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
        Предпросмотр документа — нажмите страницу, чтобы открыть крупно. После оплаты
        скачаете чистый файл без водяного знака.
      </div>

      <div className="space-y-3">
        {pages.map((url, i) =>
          broken.has(i) ? (
            <div
              key={i}
              className="flex flex-col items-center justify-center gap-2 rounded-lg border border-gray-200 bg-gray-50 py-10 text-sm text-gray-400"
            >
              <ImageOff className="h-5 w-5" />
              Страница {i + 1} не загрузилась
              <button onClick={load} className="text-blue-600 hover:underline">
                Обновить
              </button>
            </div>
          ) : (
            <div
              key={i}
              className="overflow-hidden rounded-lg border border-gray-200 shadow-sm"
            >
              <button
                type="button"
                onClick={() => setOpenAt(i)}
                className="block w-full"
                aria-label={`Открыть страницу ${i + 1}`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={url}
                  alt={`Страница ${i + 1}`}
                  draggable={false}
                  onError={() => setBroken((prev) => new Set(prev).add(i))}
                  className="w-full select-none"
                />
              </button>
              {/* Кнопка всегда видна (в т.ч. на телефоне, где нет hover). */}
              <button
                type="button"
                onClick={() => setOpenAt(i)}
                className="flex w-full items-center justify-center gap-1.5 border-t border-gray-100 bg-gray-50 py-2.5 text-sm font-medium text-primary hover:bg-gray-100"
              >
                <Maximize2 className="h-4 w-4" />
                Страница {i + 1} — открыть
              </button>
            </div>
          ),
        )}
      </div>

      {openAt !== null && (
        <PreviewModal
          pages={pages}
          index={openAt}
          onClose={() => setOpenAt(null)}
          onNav={(next) => setOpenAt(next)}
        />
      )}
    </div>
  );
}

function PreviewModal({
  pages,
  index,
  onClose,
  onNav,
}: {
  pages: string[];
  index: number;
  onClose: () => void;
  onNav: (next: number) => void;
}) {
  const hasPrev = index > 0;
  const hasNext = index < pages.length - 1;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <button
        onClick={onClose}
        className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        aria-label="Закрыть"
      >
        <X className="h-5 w-5" />
      </button>

      {hasPrev && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onNav(index - 1);
          }}
          className="absolute left-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
          aria-label="Предыдущая страница"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      )}

      <div className="flex max-h-[90vh] flex-col items-center" onClick={(e) => e.stopPropagation()}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={pages[index]}
          alt={`Страница ${index + 1}`}
          draggable={false}
          className="max-h-[85vh] w-auto select-none rounded-lg shadow-2xl"
        />
        <p className="mt-3 text-sm text-white/70">
          Страница {index + 1} из {pages.length}
        </p>
      </div>

      {hasNext && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onNav(index + 1);
          }}
          className="absolute right-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
          aria-label="Следующая страница"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      )}
    </div>
  );
}

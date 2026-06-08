"use client";

import { useEffect, useState } from "react";
import { CheckCircle, X } from "lucide-react";

/**
 * Тост «Документ готов» в правом нижнем углу.
 *
 * Появляется, когда заказ переходит в done, пока пользователь на странице
 * (push-уведомлений нет — это inline-сигнал). Сам уезжает через autoHideMs;
 * закрывается крестиком.
 */
export function OrderReadyToast({
  open,
  onClose,
  title = "Документ готов",
  description = "Файл можно скачать ниже и он отправлен на вашу почту.",
  autoHideMs = 8000,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  autoHideMs?: number;
}) {
  // Отдельный visible-стейт, чтобы проиграть transition входа/выхода.
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!open) {
      setVisible(false);
      return;
    }
    // Следующий кадр — иначе элемент монтируется уже в конечном состоянии без анимации.
    const raf = requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(onClose, autoHideMs);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timer);
    };
  }, [open, autoHideMs, onClose]);

  if (!open) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-4 right-4 z-50 max-w-sm transition-all duration-300 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
      }`}
    >
      <div className="flex items-start gap-3 rounded-xl border border-green-100 bg-white p-4 shadow-lg">
        <CheckCircle className="h-6 w-6 shrink-0 text-green-600" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-900">{title}</p>
          <p className="mt-0.5 text-sm text-gray-500">{description}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Закрыть уведомление"
          className="shrink-0 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

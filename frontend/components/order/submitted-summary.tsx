"use client";

import { useEffect, useState } from "react";
import { ClipboardCheck } from "lucide-react";

interface SummaryItem {
  label: string;
  value: string;
}

// Сводка «что вы вписали» на экране готового документа — пользователь сверяет
// введённые данные с тем, что попало в документ. Сворачивается/разворачивается.
export function SubmittedSummary({ orderId }: { orderId: string }) {
  const [items, setItems] = useState<SummaryItem[] | null>(null);
  const [open, setOpen] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await fetch(`/api/orders/${orderId}/summary`, { cache: "no-store" });
        if (!res.ok) return;
        const data: { items: SummaryItem[] } = await res.json();
        if (active) setItems(data.items ?? []);
      } catch {
        /* тихо: сводка — вспомогательный блок, не критична */
      }
    })();
    return () => {
      active = false;
    };
  }, [orderId]);

  if (!items || items.length === 0) return null;

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 text-left">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-sm font-semibold text-gray-900"
      >
        <span className="flex items-center gap-2">
          <ClipboardCheck className="h-4 w-4 text-primary" />
          Проверьте свои данные
        </span>
        <span className="text-xs font-normal text-gray-400">{open ? "Свернуть" : "Показать"}</span>
      </button>

      {open && (
        <dl className="divide-y divide-gray-200 border-t border-gray-200 px-4 pb-2">
          {items.map((it, i) => (
            <div key={i} className="flex gap-3 py-2 text-sm">
              <dt className="w-2/5 shrink-0 text-gray-500">{it.label}</dt>
              <dd className="flex-1 text-gray-900 break-words whitespace-pre-wrap">{it.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

export function DevPaymentForm({ orderId }: { orderId: string }) {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function simulatePaid() {
    setStatus("loading");
    setError(null);
    try {
      const res = await fetch("/api/dev/simulate-payment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_id: orderId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError((body as { error?: string }).error ?? `Ошибка ${res.status}`);
        setStatus("error");
        return;
      }
      setStatus("done");
      router.push(`/orders/${orderId}`);
    } catch {
      setError("Не удалось подключиться к серверу.");
      setStatus("error");
    }
  }

  return (
    <div className="space-y-3">
      <Button
        onClick={simulatePaid}
        disabled={status === "loading" || status === "done"}
        className="w-full h-12 text-base"
      >
        {status === "loading" ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Симулируем оплату…
          </>
        ) : status === "done" ? (
          "Готово! Перенаправляем…"
        ) : (
          "Оплатить (dev)"
        )}
      </Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <p className="text-xs text-gray-300">
        Вызывает POST /api/dev/simulate-payment → webhook yookassa
      </p>
    </div>
  );
}

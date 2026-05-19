"use client";

import { useEffect, useState } from "react";
import { CheckCircle, Clock, Download, FileText, Loader2, XCircle, RefreshCcw, PlusCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface Order {
  id: string;
  situation_id: string;
  status: string;
  amount: number;
  created_at: string;
  paid_at: string | null;
  payment_url: string | null;
}

type StatusConfig = {
  icon: React.ReactNode;
  label: string;
  description: string;
  terminal: boolean;
};

const STATUS_CONFIG: Record<string, StatusConfig> = {
  draft: {
    icon: <Clock className="h-8 w-8 text-gray-400" />,
    label: "Ожидание оплаты",
    description: "Нажмите кнопку ниже, чтобы оплатить и запустить создание документа.",
    terminal: false,
  },
  pending_payment: {
    icon: <Clock className="h-8 w-8 text-yellow-500" />,
    label: "Ожидание оплаты",
    description: "Платёж создан. Если вы закрыли страницу оплаты — нажмите кнопку ниже.",
    terminal: false,
  },
  paid: {
    icon: <CheckCircle className="h-8 w-8 text-green-500" />,
    label: "Оплачено",
    description: "Оплата получена. Начинаем подготовку документа.",
    terminal: false,
  },
  generating: {
    icon: <Loader2 className="h-8 w-8 text-primary animate-spin" />,
    label: "Создаём документ",
    description: "Документ готовится — обычно это занимает меньше минуты.",
    terminal: false,
  },
  done: {
    icon: <FileText className="h-8 w-8 text-green-600" />,
    label: "Документ готов",
    description: "Документ отправлен на вашу почту и доступен для скачивания.",
    terminal: true,
  },
  failed: {
    icon: <XCircle className="h-8 w-8 text-red-500" />,
    label: "Ошибка генерации",
    description: "Что-то пошло не так. Мы уже получили уведомление — проверьте почту или напишите нам.",
    terminal: true,
  },
};

const POLL_STATUSES = new Set(["paid", "generating"]);

function ymGoal(goal: string, params?: Record<string, unknown>) {
  const id = Number(process.env.NEXT_PUBLIC_YM_COUNTER_ID);
  if (id && typeof window !== "undefined" && window.ym) {
    window.ym(id, "reachGoal", goal, params);
  }
}

export function OrderStatus({
  orderId,
  initialOrder,
}: {
  orderId: string;
  initialOrder: Order;
}) {
  const [order, setOrder] = useState<Order>(initialOrder);
  const [payError, setPayError] = useState<string | null>(null);
  const [isPaying, setIsPaying] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  // Poll status while processing
  useEffect(() => {
    if (!POLL_STATUSES.has(order.status)) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/orders/${orderId}`, { cache: "no-store" });
        if (res.ok) {
          const data: Order = await res.json();
          setOrder(data);
          if (!POLL_STATUSES.has(data.status)) clearInterval(interval);
        }
      } catch {
        // network blip — keep polling
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [orderId, order.status]);

  useEffect(() => {
    if (order.status !== "paid") return;
    const key = `ym_ps_${orderId}`;
    try {
      if (!sessionStorage.getItem(key)) {
        ymGoal("payment_success", { situation: order.situation_id });
        sessionStorage.setItem(key, "1");
      }
    } catch {}
  }, [order.status, orderId]);

  async function handleRetry() {
    setIsRetrying(true);
    setRetryError(null);
    try {
      const res = await fetch(`/api/orders/${orderId}/retry`, { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setRetryError(data.error ?? "Не удалось запустить повторную генерацию.");
        return;
      }
      setOrder((prev) => ({ ...prev, status: "generating" }));
    } catch {
      setRetryError("Не удалось связаться с сервером. Попробуйте позже.");
    } finally {
      setIsRetrying(false);
    }
  }

  async function handlePay() {
    setIsPaying(true);
    setPayError(null);
    ymGoal("payment_initiated", { situation: order.situation_id });
    try {
      const res = await fetch(`/api/orders/${orderId}/pay`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setPayError(data.error ?? "Ошибка при создании платежа. Попробуйте ещё раз.");
        return;
      }
      window.location.href = data.payment_url;
    } catch {
      setPayError("Не удалось создать платёж. Попробуйте позже или напишите на lawdocsru@gmail.com.");
    } finally {
      setIsPaying(false);
    }
  }

  const cfg = STATUS_CONFIG[order.status] ?? STATUS_CONFIG["failed"]!;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center space-y-6">
      <div className="flex justify-center">{cfg.icon}</div>

      <div>
        <p className="text-lg font-semibold text-gray-900">{cfg.label}</p>
        <p className="text-gray-500 text-sm mt-1">{cfg.description}</p>
      </div>

      {(order.status === "draft" || order.status === "pending_payment") && (
        <div className="space-y-3">
          {order.status === "pending_payment" && order.payment_url ? (
            <a
              href={order.payment_url}
              className="w-full h-12 text-base inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/80 font-medium transition-colors"
            >
              Перейти к оплате →
            </a>
          ) : (
            <Button
              onClick={handlePay}
              disabled={isPaying}
              className="w-full h-12 text-base"
            >
              {isPaying ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Перенаправляем…
                </>
              ) : (
                `Оплатить ${(order.amount / 100).toFixed(0)} ₽`
              )}
            </Button>
          )}
          {order.status === "pending_payment" && (
            <button
              onClick={handlePay}
              disabled={isPaying}
              className="text-xs text-gray-400 hover:text-gray-600 underline w-full text-center"
            >
              {isPaying ? "Создаём новый платёж…" : "Ссылка устарела? Создать новый платёж"}
            </button>
          )}
          {payError && <p className="text-sm text-red-600">{payError}</p>}
        </div>
      )}

      {order.status === "done" && (
        <div className="flex flex-col sm:flex-row gap-3">
          <a
            href={`/api/documents/${orderId}/download/docx`}
            download
            onClick={() => ymGoal("document_downloaded", { format: "docx", situation: order.situation_id })}
            className="flex-1 flex items-center justify-center gap-2 h-11 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors"
          >
            <Download className="h-4 w-4" />
            Скачать Word
          </a>
          <a
            href={`/api/documents/${orderId}/download/pdf`}
            download
            onClick={() => ymGoal("document_downloaded", { format: "pdf", situation: order.situation_id })}
            className="flex-1 flex items-center justify-center gap-2 h-11 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-primary-foreground transition-colors"
          >
            <Download className="h-4 w-4" />
            Скачать PDF
          </a>
        </div>
      )}

      {order.status === "done" && (
        <a
          href={`/api/documents/${orderId}/download/instruction`}
          download
          className="flex items-center justify-center gap-2 h-11 rounded-lg border border-primary/20 bg-primary/5 hover:bg-primary/10 text-sm font-medium text-primary transition-colors w-full"
        >
          <FileText className="h-4 w-4" />
          Скачать инструкцию (куда подать и что делать дальше)
        </a>
      )}


      {order.status === "done" && (
        <>
          <p className="text-xs text-gray-400">
            PDF также отправлен на вашу почту.{" "}
            <a href="mailto:lawdocsru@gmail.com" className="text-primary hover:underline">
              Не получили?
            </a>
          </p>
          <Link
            href="/situations"
            className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
          >
            <PlusCircle className="h-4 w-4" />
            Создать ещё один документ
          </Link>
        </>
      )}

      {order.status === "failed" && (
        <div className="flex flex-col gap-3">
          <Button
            onClick={handleRetry}
            disabled={isRetrying}
            className="w-full h-11 text-base"
          >
            {isRetrying ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Запускаем…
              </>
            ) : (
              <>
                <RefreshCcw className="h-4 w-4 mr-2" />
                Попробовать ещё раз
              </>
            )}
          </Button>
          {retryError && <p className="text-sm text-red-600">{retryError}</p>}
          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href={`/wizard/${order.situation_id}`}
              className="flex-1 flex items-center justify-center gap-2 h-10 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors"
            >
              <RefreshCcw className="h-4 w-4" />
              Заполнить заново
            </Link>
            <a
              href="mailto:lawdocsru@gmail.com"
              className="flex-1 flex items-center justify-center gap-2 h-10 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-primary-foreground transition-colors"
            >
              Написать в поддержку
            </a>
          </div>
        </div>
      )}

      <p className="text-xs text-gray-300">
        Заказ № {orderId.slice(0, 8).toUpperCase()}
      </p>
    </div>
  );
}

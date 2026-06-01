"use client";

import { useEffect, useState } from "react";
import { CheckCircle, Clock, FileText, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { E2EEClient } from "@/lib/e2ee-client";
import { ymGoal } from "@/lib/analytics";
import { downloadDocument, MissingKeyError } from "@/lib/e2ee-download";
import { RecoverAccessInline } from "@/components/order/recover-access-inline";
import { fetchOrder, retryOrder, payOrder } from "@/lib/api-client";
import { PaySection, DoneSection, FailedSection, RefundedSection } from "@/components/order/order-status-sections";
import type { OrderStatus as OrderStatusValue } from "@/lib/api-schemas";

interface Order {
  id: string;
  situation_id: string;
  status: OrderStatusValue;
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

const STATUS_CONFIG: Record<OrderStatusValue, StatusConfig> = {
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
  refunded: {
    icon: <CheckCircle className="h-8 w-8 text-gray-500" />,
    label: "Деньги возвращены",
    description: "Документ создать не удалось, поэтому мы автоматически вернули оплату. Возврат придёт на карту в течение нескольких дней.",
    terminal: true,
  },
};

// pending_payment включён: заказ уже создан и ждёт вебхук ЮKassa — после возврата
// с оплаты статус сменится на generating, фронт должен подхватить это сам.
// draft НЕ опрашиваем — там ещё не платили, опрос был бы лишней нагрузкой.
const POLL_STATUSES = new Set(["pending_payment", "paid", "generating"]);

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
  const [downloadingFmt, setDownloadingFmt] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  // Формат, который юзер пытался скачать без ключа — повторим после восстановления.
  const [pendingFmt, setPendingFmt] = useState<"docx" | "pdf" | null>(null);

  async function handleDownload(fmt: "docx" | "pdf") {
    setDownloadingFmt(fmt);
    setDownloadError(null);
    try {
      await downloadDocument(orderId, fmt, order.situation_id);
    } catch (e) {
      if (e instanceof MissingKeyError) {
        setPendingFmt(fmt); // покажем форму восстановления, повторим скачивание после
      } else {
        setDownloadError(e instanceof Error ? e.message : "Ошибка скачивания");
      }
    } finally {
      setDownloadingFmt(null);
    }
  }

  // Poll status while processing
  useEffect(() => {
    if (!POLL_STATUSES.has(order.status)) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetchOrder(orderId);
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

  // Refetch при возврате на вкладку (например, после оплаты на ЮKassa).
  // Закрывает гонку: юзер вернулся раньше, чем пришёл вебхук, и статус
  // на странице остался pending_payment, пока polling ещё не подхватил.
  useEffect(() => {
    if (!POLL_STATUSES.has(order.status)) return;

    async function refresh() {
      if (document.visibilityState !== "visible") return;
      try {
        const res = await fetchOrder(orderId);
        if (res.ok) setOrder(await res.json());
      } catch {
        // network blip — polling всё равно повторит
      }
    }

    document.addEventListener("visibilitychange", refresh);
    window.addEventListener("focus", refresh);
    return () => {
      document.removeEventListener("visibilitychange", refresh);
      window.removeEventListener("focus", refresh);
    };
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
      const res = await retryOrder(orderId);
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
      const res = await payOrder(orderId);
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

      {(order.status === "draft" || order.status === "pending_payment") && !E2EEClient.hasKeys() && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-left">
          <p className="text-sm text-amber-800">
            Доступ к документам не настроен в этом браузере. Готовый файл шифруется вашим ключом — без него вы не сможете его открыть здесь.{" "}
            <Link href="/login" className="font-medium underline hover:no-underline">
              Войдите на устройстве, где настраивали доступ
            </Link>
            , или восстановите доступ перед оплатой.
          </p>
        </div>
      )}

      {(order.status === "draft" || order.status === "pending_payment") && (
        <PaySection order={order} isPaying={isPaying} payError={payError} onPay={handlePay} />
      )}

      {order.status === "done" && (
        <DoneSection
          orderId={orderId}
          order={order}
          downloadingFmt={downloadingFmt}
          downloadError={downloadError}
          onDownload={handleDownload}
          needsKeyFor={pendingFmt}
          onRecovered={() => {
            const fmt = pendingFmt;
            setPendingFmt(null);
            if (fmt) handleDownload(fmt);
          }}
        />
      )}

      {order.status === "failed" && (
        <FailedSection order={order} isRetrying={isRetrying} retryError={retryError} onRetry={handleRetry} />
      )}

      {order.status === "refunded" && <RefundedSection order={order} />}

      <p className="text-xs text-gray-300">
        Заказ № {orderId.slice(0, 8).toUpperCase()}
      </p>
    </div>
  );
}
